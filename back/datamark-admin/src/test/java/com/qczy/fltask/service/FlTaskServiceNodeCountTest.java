package com.qczy.fltask.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.qczy.fltask.mapper.FlTaskMapper;
import com.qczy.fltask.mapper.FlTaskRoundMetricMapper;
import com.qczy.fltask.model.dto.FlTaskCreateRequest;
import com.qczy.fltask.model.dto.FlTaskView;
import com.qczy.fltask.model.entity.FlTaskEntity;
import com.qczy.fltask.runner.FlowerRunnerClient;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class FlTaskServiceNodeCountTest {

    private static final String TASK_ID = "fl_test_001";

    @Mock
    private FlTaskMapper flTaskMapper;

    @Mock
    private FlTaskRoundMetricMapper flTaskRoundMetricMapper;

    @Mock
    private FlowerRunnerClient flowerRunnerClient;

    @Mock
    private ObjectMapper objectMapper;

    @InjectMocks
    private FlTaskService flTaskService;

    @BeforeEach
    void setUp() throws Exception {
        ReflectionTestUtils.setField(flTaskService, "runnerAppDir", "linux_flower_demo");
        ReflectionTestUtils.setField(flTaskService, "runnerRunsDir", "linux_flower_demo/runs");
        when(objectMapper.writeValueAsString(any())).thenReturn("{}");
    }

    @Test
    void shouldPersistNodeCountOnCreateTask() {
        FlTaskCreateRequest request = buildCreateRequest();

        FlTaskView view = flTaskService.createTask(request);

        ArgumentCaptor<FlTaskEntity> entityCaptor = ArgumentCaptor.forClass(FlTaskEntity.class);
        verify(flTaskMapper).insert(entityCaptor.capture());
        FlTaskEntity savedEntity = entityCaptor.getValue();

        assertEquals(3, savedEntity.getNodeCount());
        assertEquals(3, view.getNodeCount());
    }

    @Test
    void shouldRejectCreateTaskWhenNodeCountIsMissing() {
        FlTaskCreateRequest request = buildCreateRequest();
        request.setNodeCount(null);

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> flTaskService.createTask(request)
        );

        assertEquals("nodeCount must be greater than 0", exception.getMessage());
    }

    @Test
    void shouldPassNodeCountToRunnerWhenStartingTask() {
        FlTaskEntity task = buildTask();
        when(flTaskMapper.selectOne(any())).thenReturn(task, null, task);
        when(flowerRunnerClient.createTask(any())).thenReturn(status("RUNNING"));
        when(flowerRunnerClient.getTaskRounds(TASK_ID, 0)).thenReturn(Collections.<Map<String, Object>>emptyList());
        when(flowerRunnerClient.getTaskStatus(TASK_ID)).thenReturn(status("RUNNING"));

        flTaskService.startTask(TASK_ID);

        ArgumentCaptor<Map<String, Object>> payloadCaptor = ArgumentCaptor.forClass(Map.class);
        verify(flowerRunnerClient).createTask(payloadCaptor.capture());

        Map<String, Object> payload = payloadCaptor.getValue();
        Map<?, ?> runConfig = (Map<?, ?>) payload.get("runConfig");
        Map<?, ?> federationConfig = (Map<?, ?>) payload.get("federationConfig");

        assertEquals(3, runConfig.get("node-count"));
        assertEquals(3, federationConfig.get("options.num-supernodes"));
    }

    private FlTaskCreateRequest buildCreateRequest() {
        FlTaskCreateRequest request = new FlTaskCreateRequest();
        request.setName("demo");
        request.setTaskType("detection");
        request.setDatasetName("sample");
        request.setDatasetPath("linux_flower_demo/allDatasets/sample");
        request.setDatasetFormat("VOC");
        request.setModelSource("linux_flower_demo/weights/yolov8n.pt");
        request.setNumRounds(5);
        request.setNodeCount(3);
        request.setLocalEpochs(1);
        request.setBatchSize(8);
        request.setLearningRate(new BigDecimal("0.01"));
        request.setFractionEvaluate(new BigDecimal("1.0"));
        return request;
    }

    private FlTaskEntity buildTask() {
        FlTaskEntity task = new FlTaskEntity();
        task.setId(1L);
        task.setTaskId(TASK_ID);
        task.setName("demo");
        task.setStatus("CREATED");
        task.setTaskType("detection");
        task.setDatasetName("sample");
        task.setDatasetPath("linux_flower_demo/allDatasets/sample");
        task.setDatasetFormat("VOC");
        task.setModelSource("linux_flower_demo/weights/yolov8n.pt");
        task.setNumRounds(5);
        task.setNodeCount(3);
        task.setCurrentRound(0);
        task.setLocalEpochs(1);
        task.setBatchSize(8);
        task.setLearningRate(new BigDecimal("0.01"));
        task.setFractionEvaluate(new BigDecimal("1.0"));
        task.setWorkDir("linux_flower_demo/runs/" + TASK_ID);
        task.setCreatedAt(LocalDateTime.of(2026, 3, 19, 10, 0));
        return task;
    }

    private Map<String, Object> status(String status) {
        Map<String, Object> payload = new LinkedHashMap<String, Object>();
        payload.put("status", status);
        payload.put("currentRound", 0);
        return payload;
    }
}
