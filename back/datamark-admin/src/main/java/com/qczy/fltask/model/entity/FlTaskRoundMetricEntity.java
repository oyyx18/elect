package com.qczy.fltask.model.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("fl_task_round_metric")
public class FlTaskRoundMetricEntity {

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    @TableField("task_id")
    private String taskId;

    @TableField("round_no")
    private Integer roundNo;

    @TableField("loss")
    private BigDecimal loss;

    @TableField("primary_metric")
    private BigDecimal primaryMetric;

    @TableField("metrics_json")
    private String metricsJson;

    @TableField("created_at")
    private LocalDateTime createdAt;
}
