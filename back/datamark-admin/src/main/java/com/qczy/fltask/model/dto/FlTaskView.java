package com.qczy.fltask.model.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Map;

@Data
public class FlTaskView {

    private String taskId;

    private String name;

    private String status;

    private String taskType;

    private String datasetName;

    private String datasetPath;

    private String datasetFormat;

    private String modelSource;

    private Integer numRounds;

    private Integer nodeCount;

    private Integer currentRound;

    private Integer progressPercent;

    private String finalMetricName;

    private BigDecimal finalMetricValue;

    private Map<String, Object> latestMetrics;

    private Map<String, Object> finalMetrics;

    private String finalModelPath;

    private String workDir;

    private String errorMessage;

    private LocalDateTime createdAt;

    private LocalDateTime startedAt;

    private LocalDateTime finishedAt;
}
