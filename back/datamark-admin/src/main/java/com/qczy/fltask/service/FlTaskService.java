package com.qczy.fltask.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.qczy.fltask.mapper.FlTaskMapper;
import com.qczy.fltask.mapper.FlTaskRoundMetricMapper;
import com.qczy.fltask.model.dto.FlDatasetView;
import com.qczy.fltask.model.dto.FlTaskCreateRequest;
import com.qczy.fltask.model.dto.FlTaskRoundMetricView;
import com.qczy.fltask.model.dto.FlTaskView;
import com.qczy.fltask.model.entity.FlTaskEntity;
import com.qczy.fltask.model.entity.FlTaskRoundMetricEntity;
import com.qczy.fltask.runner.FlowerRunnerClient;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.IOException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class FlTaskService {

    private static final Logger log = LoggerFactory.getLogger(FlTaskService.class);

    private static final String STATUS_CREATED = "CREATED";
    private static final String STATUS_RUNNING = "RUNNING";
    private static final String STATUS_COMPLETED = "COMPLETED";
    private static final String STATUS_STOPPED = "STOPPED";

    @Value("${flower.runner.app-dir:linux_flower_demo}")
    private String runnerAppDir;

    @Value("${flower.runner.runs-dir:linux_flower_demo/runs}")
    private String runnerRunsDir;

    @Autowired
    private FlTaskMapper flTaskMapper;

    @Autowired
    private FlTaskRoundMetricMapper flTaskRoundMetricMapper;

    @Autowired
    private FlowerRunnerClient flowerRunnerClient;

    @Autowired
    private ObjectMapper objectMapper;

    @Transactional
    public FlTaskView createTask(FlTaskCreateRequest request) {
        validateCreateRequest(request);

        LocalDateTime now = LocalDateTime.now();
        FlTaskEntity entity = new FlTaskEntity();
        entity.setTaskId(generateTaskId());
        entity.setName(request.getName().trim());
        entity.setStatus(STATUS_CREATED);
        entity.setTaskType(normalizeTaskType(request.getTaskType()));
        entity.setDatasetName(resolveDatasetName(request));
        entity.setDatasetPath(request.getDatasetPath().trim());
        entity.setDatasetFormat(StringUtils.upperCase(StringUtils.defaultIfBlank(request.getDatasetFormat(), "VOC")));
        entity.setModelSource(StringUtils.trimToNull(request.getModelSource()));
        entity.setNumRounds(request.getNumRounds());
        entity.setNodeCount(request.getNodeCount());
        entity.setCurrentRound(0);
        entity.setLocalEpochs(request.getLocalEpochs());
        entity.setBatchSize(request.getBatchSize());
        entity.setLearningRate(request.getLearningRate());
        entity.setFractionEvaluate(request.getFractionEvaluate());
        entity.setWorkDir(joinPath(runnerRunsDir, entity.getTaskId()));
        entity.setConfigJson(writeJson(buildConfigSnapshot(request)));
        entity.setCreatedAt(now);
        entity.setUpdatedAt(now);

        flTaskMapper.insert(entity);
        return toView(entity);
    }

    @Transactional(readOnly = true)
    public Map<String, Object> listTasks(String status, String name, long page, long size) {
        Page<FlTaskEntity> pageParam = new Page<FlTaskEntity>(Math.max(page, 1), Math.max(size, 1));
        LambdaQueryWrapper<FlTaskEntity> queryWrapper = new LambdaQueryWrapper<FlTaskEntity>();
        if (StringUtils.isNotBlank(status)) {
            queryWrapper.eq(FlTaskEntity::getStatus, status.trim().toUpperCase());
        }
        if (StringUtils.isNotBlank(name)) {
            queryWrapper.like(FlTaskEntity::getName, name.trim());
        }
        queryWrapper.orderByDesc(FlTaskEntity::getCreatedAt);

        IPage<FlTaskEntity> result = flTaskMapper.selectPage(pageParam, queryWrapper);
        Map<String, Object> payload = new LinkedHashMap<String, Object>();
        payload.put("total", result.getTotal());
        payload.put("current", result.getCurrent());
        payload.put("size", result.getSize());
        payload.put("records", result.getRecords().stream().map(this::toView).collect(Collectors.toList()));
        return payload;
    }

    @Transactional
    public FlTaskView getTask(String taskId) {
        FlTaskEntity entity = requireTask(taskId);
        if (STATUS_RUNNING.equals(entity.getStatus())) {
            syncSingleTask(entity);
            entity = requireTask(taskId);
        }
        return toView(entity);
    }

    @Transactional(readOnly = true)
    public List<FlTaskRoundMetricView> listRounds(String taskId) {
        requireTask(taskId);
        LambdaQueryWrapper<FlTaskRoundMetricEntity> queryWrapper = new LambdaQueryWrapper<FlTaskRoundMetricEntity>()
                .eq(FlTaskRoundMetricEntity::getTaskId, taskId)
                .orderByAsc(FlTaskRoundMetricEntity::getRoundNo);
        return flTaskRoundMetricMapper.selectList(queryWrapper)
                .stream()
                .map(this::toRoundMetricView)
                .collect(Collectors.toList());
    }

    @Transactional
    public FlTaskView startTask(String taskId) {
        FlTaskEntity entity = requireTask(taskId);
        if (STATUS_RUNNING.equals(entity.getStatus())) {
            return toView(entity);
        }
        if (!STATUS_CREATED.equals(entity.getStatus())) {
            throw new IllegalArgumentException("Only CREATED tasks can be started");
        }
        if (hasOtherRunningTask(taskId)) {
            throw new IllegalArgumentException("Another Flower task is already running");
        }

        Map<String, Object> response = flowerRunnerClient.createTask(buildRunnerPayload(entity));
        entity.setStatus(readString(response.get("status"), STATUS_RUNNING));
        entity.setStartedAt(LocalDateTime.now());
        entity.setUpdatedAt(LocalDateTime.now());
        entity.setErrorMessage(null);
        flTaskMapper.updateById(entity);

        syncSingleTask(entity);
        return toView(requireTask(taskId));
    }

    @Transactional
    public FlTaskView stopTask(String taskId) {
        FlTaskEntity entity = requireTask(taskId);
        Map<String, Object> runnerHealth = getRunnerHealthForStop(taskId);
        if (!isTaskActuallyRunning(taskId, runnerHealth)) {
            if (canCollapseToStopped(entity)) {
                persistStoppedTask(entity);
                return toView(requireTask(taskId));
            }
            return toView(entity);
        }

        try {
            flowerRunnerClient.stopTask(taskId);
        } catch (Exception ex) {
            Map<String, Object> latestRunnerHealth = getRunnerHealthForStop(taskId);
            if (isTaskActuallyRunning(taskId, latestRunnerHealth)) {
                throw new IllegalStateException("Failed to stop Flower task " + taskId + ": " + ex.getMessage(), ex);
            }
            log.info("Collapse Flower task {} to STOPPED after runner already cleared it", taskId, ex);
        }

        Map<String, Object> runnerHealthAfterStop = getRunnerHealthForStop(taskId);
        if (isTaskActuallyRunning(taskId, runnerHealthAfterStop)) {
            throw new IllegalStateException("Flower runner still reports task " + taskId + " as active after stop request");
        }

        persistStoppedTask(entity);
        return toView(requireTask(taskId));
    }

    @Transactional(readOnly = true)
    public List<FlDatasetView> listDatasets() {
        return flowerRunnerClient.listDatasets()
                .stream()
                .map(this::toDatasetView)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public Map<String, Object> getRunnerHealth() {
        return flowerRunnerClient.getHealth();
    }

    @Scheduled(fixedDelayString = "${flower.runner.sync-interval-ms:5000}")
    @Transactional
    public void syncRunningTasks() {
        try {
            LambdaQueryWrapper<FlTaskEntity> queryWrapper = new LambdaQueryWrapper<FlTaskEntity>()
                    .eq(FlTaskEntity::getStatus, STATUS_RUNNING);
            List<FlTaskEntity> runningTasks = flTaskMapper.selectList(queryWrapper);
            for (FlTaskEntity task : runningTasks) {
                syncSingleTask(task);
            }
        } catch (Exception ex) {
            log.warn("Failed to sync running Flower tasks", ex);
        }
    }

    private void syncSingleTask(FlTaskEntity task) {
        try {
            int afterRound = findMaxRound(task.getTaskId());
            List<Map<String, Object>> newRounds = flowerRunnerClient.getTaskRounds(task.getTaskId(), afterRound);
            persistRoundMetrics(task, newRounds);

            Map<String, Object> statusPayload = flowerRunnerClient.getTaskStatus(task.getTaskId());
            applyRunnerStatus(task, statusPayload);
            task.setUpdatedAt(LocalDateTime.now());
            flTaskMapper.updateById(task);
        } catch (Exception ex) {
            log.warn("Failed to sync Flower task {}", task.getTaskId(), ex);
        }
    }

    private void persistRoundMetrics(FlTaskEntity task, List<Map<String, Object>> items) {
        if (items == null || items.isEmpty()) {
            return;
        }

        for (Map<String, Object> item : items) {
            Integer roundNo = readInteger(item.get("roundNo"));
            if (roundNo == null) {
                continue;
            }

            Map<String, Object> metrics = readMap(item.get("metrics"));
            FlTaskRoundMetricEntity entity = new FlTaskRoundMetricEntity();
            entity.setTaskId(task.getTaskId());
            entity.setRoundNo(roundNo);
            entity.setLoss(readDecimal(metrics.get("loss")));
            entity.setPrimaryMetric(resolvePrimaryMetricValue(task.getTaskType(), metrics));
            entity.setMetricsJson(writeJson(metrics));
            entity.setCreatedAt(parseDateTime(readString(item.get("timestamp"), null), LocalDateTime.now()));
            try {
                flTaskRoundMetricMapper.insert(entity);
            } catch (Exception ex) {
                log.debug("Skip duplicated round metric for task {} round {}", task.getTaskId(), roundNo, ex);
            }
        }
    }

    private void applyRunnerStatus(FlTaskEntity task, Map<String, Object> statusPayload) {
        String status = readString(statusPayload.get("status"), task.getStatus());
        Map<String, Object> latestMetrics = readMap(statusPayload.get("latestMetrics"));
        Map<String, Object> finalMetrics = readMap(statusPayload.get("finalMetrics"));

        task.setStatus(status);
        Integer currentRound = readInteger(statusPayload.get("currentRound"));
        if (currentRound != null) {
            task.setCurrentRound(currentRound);
        }
        if (!latestMetrics.isEmpty()) {
            task.setLatestMetricsJson(writeJson(latestMetrics));
        }
        if (!finalMetrics.isEmpty()) {
            task.setFinalMetricsJson(writeJson(finalMetrics));
            task.setFinalMetricName(resolvePrimaryMetricName(task.getTaskType(), finalMetrics));
            task.setFinalMetricValue(resolvePrimaryMetricValue(task.getTaskType(), finalMetrics));
        } else if (!latestMetrics.isEmpty()) {
            task.setFinalMetricName(resolvePrimaryMetricName(task.getTaskType(), latestMetrics));
            task.setFinalMetricValue(resolvePrimaryMetricValue(task.getTaskType(), latestMetrics));
        }

        String finalModelPath = readString(statusPayload.get("finalModelPath"), null);
        if (StringUtils.isNotBlank(finalModelPath)) {
            task.setFinalModelPath(finalModelPath);
        }

        String errorMessage = readString(statusPayload.get("errorMessage"), null);
        if (StringUtils.isNotBlank(errorMessage)) {
            task.setErrorMessage(errorMessage);
        }

        task.setStartedAt(parseDateTime(readString(statusPayload.get("startedAt"), null), task.getStartedAt()));
        task.setFinishedAt(parseDateTime(readString(statusPayload.get("finishedAt"), null), task.getFinishedAt()));
    }

    private Map<String, Object> buildRunnerPayload(FlTaskEntity entity) {
        Map<String, Object> runConfig = new LinkedHashMap<String, Object>();
        runConfig.put("task-type", entity.getTaskType());
        runConfig.put("num-server-rounds", entity.getNumRounds());
        runConfig.put("node-count", entity.getNodeCount());
        runConfig.put("local-epochs", entity.getLocalEpochs());
        runConfig.put("learning-rate", entity.getLearningRate());
        runConfig.put("batch-size", entity.getBatchSize());
        runConfig.put("fraction-evaluate", entity.getFractionEvaluate());

        Map<String, Object> federationConfig = new LinkedHashMap<String, Object>();
        federationConfig.put("options.num-supernodes", entity.getNodeCount());

        Map<String, Object> env = new LinkedHashMap<String, Object>();
        if ("detection".equalsIgnoreCase(entity.getTaskType()) && StringUtils.isNotBlank(entity.getDatasetPath())) {
            env.put("FLOWER_DETECTION_DATASET", normalizeRunnerEnvPath(entity.getDatasetPath()));
        }
        if ("detection".equalsIgnoreCase(entity.getTaskType()) && StringUtils.isNotBlank(entity.getDatasetFormat())) {
            env.put("FLOWER_DETECTION_DATASET_FORMAT", entity.getDatasetFormat().trim().toUpperCase());
        }
        if ("detection".equalsIgnoreCase(entity.getTaskType()) && StringUtils.isNotBlank(entity.getModelSource())) {
            env.put("FLOWER_YOLO_MODEL", normalizeRunnerEnvPath(entity.getModelSource()));
        }

        Map<String, Object> payload = new LinkedHashMap<String, Object>();
        payload.put("taskId", entity.getTaskId());
        payload.put("appDir", runnerAppDir);
        payload.put("workDir", entity.getWorkDir());
        payload.put("runConfig", runConfig);
        payload.put("federationConfig", federationConfig);
        payload.put("env", env);
        return payload;
    }

    private FlTaskEntity requireTask(String taskId) {
        LambdaQueryWrapper<FlTaskEntity> queryWrapper = new LambdaQueryWrapper<FlTaskEntity>()
                .eq(FlTaskEntity::getTaskId, taskId)
                .last("limit 1");
        FlTaskEntity entity = flTaskMapper.selectOne(queryWrapper);
        if (entity == null) {
            throw new IllegalArgumentException("Task not found: " + taskId);
        }
        return entity;
    }

    private FlTaskView toView(FlTaskEntity entity) {
        FlTaskView view = new FlTaskView();
        view.setTaskId(entity.getTaskId());
        view.setName(entity.getName());
        view.setStatus(entity.getStatus());
        view.setTaskType(entity.getTaskType());
        view.setDatasetName(entity.getDatasetName());
        view.setDatasetPath(entity.getDatasetPath());
        view.setDatasetFormat(entity.getDatasetFormat());
        view.setModelSource(entity.getModelSource());
        view.setNumRounds(entity.getNumRounds());
        view.setNodeCount(entity.getNodeCount());
        view.setCurrentRound(entity.getCurrentRound());
        view.setProgressPercent(calculateProgress(entity.getCurrentRound(), entity.getNumRounds()));
        view.setFinalMetricName(entity.getFinalMetricName());
        view.setFinalMetricValue(entity.getFinalMetricValue());
        view.setLatestMetrics(readJsonMap(entity.getLatestMetricsJson()));
        view.setFinalMetrics(readJsonMap(entity.getFinalMetricsJson()));
        view.setFinalModelPath(entity.getFinalModelPath());
        view.setWorkDir(entity.getWorkDir());
        view.setErrorMessage(entity.getErrorMessage());
        view.setCreatedAt(entity.getCreatedAt());
        view.setStartedAt(entity.getStartedAt());
        view.setFinishedAt(entity.getFinishedAt());
        return view;
    }

    private FlTaskRoundMetricView toRoundMetricView(FlTaskRoundMetricEntity entity) {
        FlTaskRoundMetricView view = new FlTaskRoundMetricView();
        view.setRoundNo(entity.getRoundNo());
        view.setLoss(entity.getLoss());
        view.setPrimaryMetric(entity.getPrimaryMetric());
        view.setMetrics(readJsonMap(entity.getMetricsJson()));
        view.setCreatedAt(entity.getCreatedAt());
        return view;
    }

    private FlDatasetView toDatasetView(Map<String, Object> payload) {
        FlDatasetView view = new FlDatasetView();
        view.setName(readString(payload.get("name"), null));
        view.setPath(readString(payload.get("path"), null));
        view.setFormat(readString(payload.get("format"), "UNKNOWN"));
        return view;
    }

    private void validateCreateRequest(FlTaskCreateRequest request) {
        if (request == null) {
            throw new IllegalArgumentException("Request body is required");
        }
        if (StringUtils.isBlank(request.getName())) {
            throw new IllegalArgumentException("Task name is required");
        }
        if (StringUtils.isBlank(request.getTaskType())) {
            throw new IllegalArgumentException("Task type is required");
        }
        if (!"detection".equalsIgnoreCase(request.getTaskType()) &&
                !"classification".equalsIgnoreCase(request.getTaskType())) {
            throw new IllegalArgumentException("Task type must be detection or classification");
        }
        if (StringUtils.isBlank(request.getDatasetPath())) {
            throw new IllegalArgumentException("Dataset path is required");
        }
        if (request.getNumRounds() == null || request.getNumRounds() <= 0) {
            throw new IllegalArgumentException("numRounds must be greater than 0");
        }
        if (request.getNodeCount() == null || request.getNodeCount() <= 0) {
            throw new IllegalArgumentException("nodeCount must be greater than 0");
        }
        if (request.getLocalEpochs() == null || request.getLocalEpochs() <= 0) {
            throw new IllegalArgumentException("localEpochs must be greater than 0");
        }
        if (request.getBatchSize() == null || request.getBatchSize() <= 0) {
            throw new IllegalArgumentException("batchSize must be greater than 0");
        }
        if (request.getLearningRate() == null || request.getLearningRate().compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("learningRate must be greater than 0");
        }
        if (request.getFractionEvaluate() == null || request.getFractionEvaluate().compareTo(BigDecimal.ZERO) < 0) {
            throw new IllegalArgumentException("fractionEvaluate must be greater than or equal to 0");
        }
    }

    private Map<String, Object> buildConfigSnapshot(FlTaskCreateRequest request) {
        Map<String, Object> snapshot = new LinkedHashMap<String, Object>();
        snapshot.put("name", request.getName());
        snapshot.put("taskType", normalizeTaskType(request.getTaskType()));
        snapshot.put("datasetName", request.getDatasetName());
        snapshot.put("datasetPath", request.getDatasetPath());
        snapshot.put("datasetFormat", request.getDatasetFormat());
        snapshot.put("modelSource", request.getModelSource());
        snapshot.put("numRounds", request.getNumRounds());
        snapshot.put("nodeCount", request.getNodeCount());
        snapshot.put("localEpochs", request.getLocalEpochs());
        snapshot.put("batchSize", request.getBatchSize());
        snapshot.put("learningRate", request.getLearningRate());
        snapshot.put("fractionEvaluate", request.getFractionEvaluate());
        return snapshot;
    }

    private String resolveDatasetName(FlTaskCreateRequest request) {
        if (StringUtils.isNotBlank(request.getDatasetName())) {
            return request.getDatasetName().trim();
        }
        Path path = Paths.get(request.getDatasetPath().trim());
        Path fileName = path.getFileName();
        return fileName != null ? fileName.toString() : request.getDatasetPath().trim();
    }

    private String normalizeTaskType(String taskType) {
        return taskType == null ? null : taskType.trim().toLowerCase();
    }

    private String generateTaskId() {
        return "fl_" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss")) +
                "_" + UUID.randomUUID().toString().substring(0, 6);
    }

    private int findMaxRound(String taskId) {
        LambdaQueryWrapper<FlTaskRoundMetricEntity> queryWrapper = new LambdaQueryWrapper<FlTaskRoundMetricEntity>()
                .eq(FlTaskRoundMetricEntity::getTaskId, taskId)
                .orderByDesc(FlTaskRoundMetricEntity::getRoundNo)
                .last("limit 1");
        FlTaskRoundMetricEntity entity = flTaskRoundMetricMapper.selectOne(queryWrapper);
        return entity != null && entity.getRoundNo() != null ? entity.getRoundNo() : 0;
    }

    private boolean hasOtherRunningTask(String taskId) {
        LambdaQueryWrapper<FlTaskEntity> queryWrapper = new LambdaQueryWrapper<FlTaskEntity>()
                .eq(FlTaskEntity::getStatus, STATUS_RUNNING)
                .ne(FlTaskEntity::getTaskId, taskId)
                .last("limit 1");
        return flTaskMapper.selectOne(queryWrapper) != null;
    }

    private Map<String, Object> getRunnerHealthForStop(String taskId) {
        try {
            return flowerRunnerClient.getHealth();
        } catch (Exception ex) {
            throw new IllegalStateException(
                    "Flower runner is unavailable, cannot confirm stop state for task " + taskId + ": " + ex.getMessage(),
                    ex
            );
        }
    }

    private boolean isTaskActuallyRunning(String taskId, Map<String, Object> runnerHealth) {
        return Boolean.TRUE.equals(readBoolean(runnerHealth.get("running")))
                && StringUtils.equals(taskId, readString(runnerHealth.get("activeTaskId"), null));
    }

    private boolean canCollapseToStopped(FlTaskEntity task) {
        return STATUS_RUNNING.equals(task.getStatus()) || STATUS_STOPPED.equals(task.getStatus());
    }

    private void persistStoppedTask(FlTaskEntity task) {
        LocalDateTime now = LocalDateTime.now();
        task.setStatus(STATUS_STOPPED);
        if (task.getFinishedAt() == null) {
            task.setFinishedAt(now);
        }
        task.setUpdatedAt(now);
        flTaskMapper.updateById(task);
    }

    private Map<String, Object> readJsonMap(String json) {
        if (StringUtils.isBlank(json)) {
            return null;
        }
        try {
            return objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {
            });
        } catch (IOException ex) {
            log.warn("Failed to parse json: {}", json, ex);
            return null;
        }
    }

    private String writeJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (IOException ex) {
            throw new IllegalStateException("Failed to serialize json", ex);
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> readMap(Object value) {
        if (!(value instanceof Map)) {
            return Collections.emptyMap();
        }
        return (Map<String, Object>) value;
    }

    private String readString(Object value, String defaultValue) {
        if (value == null) {
            return defaultValue;
        }
        String text = String.valueOf(value);
        return StringUtils.isBlank(text) ? defaultValue : text;
    }

    private Integer readInteger(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Number) {
            return ((Number) value).intValue();
        }
        try {
            return Integer.parseInt(String.valueOf(value));
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    private Boolean readBoolean(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Boolean) {
            return (Boolean) value;
        }
        if (value instanceof Number) {
            return ((Number) value).intValue() != 0;
        }
        String text = String.valueOf(value);
        if (StringUtils.isBlank(text)) {
            return null;
        }
        if ("true".equalsIgnoreCase(text)) {
            return Boolean.TRUE;
        }
        if ("false".equalsIgnoreCase(text)) {
            return Boolean.FALSE;
        }
        return null;
    }

    private BigDecimal readDecimal(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof BigDecimal) {
            return (BigDecimal) value;
        }
        if (value instanceof Number) {
            return BigDecimal.valueOf(((Number) value).doubleValue());
        }
        try {
            return new BigDecimal(String.valueOf(value));
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    private String resolvePrimaryMetricName(String taskType, Map<String, Object> metrics) {
        if (metrics == null || metrics.isEmpty()) {
            return null;
        }
        if ("detection".equalsIgnoreCase(taskType) && metrics.containsKey("map50")) {
            return "map50";
        }
        if ("classification".equalsIgnoreCase(taskType) && metrics.containsKey("accuracy")) {
            return "accuracy";
        }
        if (metrics.containsKey("accuracy")) {
            return "accuracy";
        }
        if (metrics.containsKey("map50")) {
            return "map50";
        }
        for (String key : metrics.keySet()) {
            if (!"loss".equalsIgnoreCase(key)) {
                return key;
            }
        }
        return null;
    }

    private BigDecimal resolvePrimaryMetricValue(String taskType, Map<String, Object> metrics) {
        String metricName = resolvePrimaryMetricName(taskType, metrics);
        return metricName == null ? null : readDecimal(metrics.get(metricName));
    }

    private Integer calculateProgress(Integer currentRound, Integer numRounds) {
        if (currentRound == null || numRounds == null || numRounds <= 0) {
            return 0;
        }
        BigDecimal progress = BigDecimal.valueOf(currentRound)
                .multiply(BigDecimal.valueOf(100))
                .divide(BigDecimal.valueOf(numRounds), 0, RoundingMode.DOWN);
        return progress.intValue();
    }

    private LocalDateTime parseDateTime(String value, LocalDateTime defaultValue) {
        if (StringUtils.isBlank(value)) {
            return defaultValue;
        }
        try {
            return OffsetDateTime.parse(value).toLocalDateTime();
        } catch (DateTimeParseException ex) {
            try {
                return LocalDateTime.parse(value);
            } catch (DateTimeParseException ignored) {
                return defaultValue;
            }
        }
    }

    private String joinPath(String base, String child) {
        String normalizedBase = StringUtils.removeEnd(base.replace('\\', '/'), "/");
        return normalizedBase + "/" + child;
    }

    private String normalizeRunnerEnvPath(String pathValue) {
        String normalizedPath = pathValue.replace('\\', '/');
        Path appPath = Paths.get(runnerAppDir);
        Path appName = appPath.getFileName();
        if (appName == null) {
            return normalizedPath;
        }

        String prefix = appName.toString().replace('\\', '/') + "/";
        if (normalizedPath.startsWith(prefix)) {
            return normalizedPath.substring(prefix.length());
        }
        return normalizedPath;
    }
}
