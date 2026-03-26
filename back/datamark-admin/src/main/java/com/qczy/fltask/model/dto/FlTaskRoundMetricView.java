package com.qczy.fltask.model.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Map;

@Data
public class FlTaskRoundMetricView {

    private Integer roundNo;

    private BigDecimal loss;

    private BigDecimal primaryMetric;

    private Map<String, Object> metrics;

    private LocalDateTime createdAt;
}
