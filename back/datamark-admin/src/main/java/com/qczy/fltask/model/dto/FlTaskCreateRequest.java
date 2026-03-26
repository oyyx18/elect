package com.qczy.fltask.model.dto;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class FlTaskCreateRequest {

    private String name;

    private String taskType;

    private String datasetName;

    private String datasetPath;

    private String datasetFormat;

    private String modelSource;

    private Integer numRounds;

    private Integer nodeCount;

    private Integer localEpochs;

    private Integer batchSize;

    private BigDecimal learningRate;

    private BigDecimal fractionEvaluate;
}
