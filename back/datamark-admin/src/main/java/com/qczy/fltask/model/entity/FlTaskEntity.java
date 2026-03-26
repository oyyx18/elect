package com.qczy.fltask.model.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("fl_task")
public class FlTaskEntity {

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    @TableField("task_id")
    private String taskId;

    @TableField("name")
    private String name;

    @TableField("status")
    private String status;

    @TableField("task_type")
    private String taskType;

    @TableField("dataset_name")
    private String datasetName;

    @TableField("dataset_path")
    private String datasetPath;

    @TableField("dataset_format")
    private String datasetFormat;

    @TableField("model_source")
    private String modelSource;

    @TableField("num_rounds")
    private Integer numRounds;

    @TableField("node_count")
    private Integer nodeCount;

    @TableField("current_round")
    private Integer currentRound;

    @TableField("local_epochs")
    private Integer localEpochs;

    @TableField("batch_size")
    private Integer batchSize;

    @TableField("learning_rate")
    private BigDecimal learningRate;

    @TableField("fraction_evaluate")
    private BigDecimal fractionEvaluate;

    @TableField("final_metric_name")
    private String finalMetricName;

    @TableField("final_metric_value")
    private BigDecimal finalMetricValue;

    @TableField("latest_metrics_json")
    private String latestMetricsJson;

    @TableField("final_metrics_json")
    private String finalMetricsJson;

    @TableField("work_dir")
    private String workDir;

    @TableField("final_model_path")
    private String finalModelPath;

    @TableField("error_message")
    private String errorMessage;

    @TableField("config_json")
    private String configJson;

    @TableField("created_at")
    private LocalDateTime createdAt;

    @TableField("started_at")
    private LocalDateTime startedAt;

    @TableField("finished_at")
    private LocalDateTime finishedAt;

    @TableField("updated_at")
    private LocalDateTime updatedAt;
}
