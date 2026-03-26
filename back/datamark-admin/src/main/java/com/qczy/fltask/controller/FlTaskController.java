package com.qczy.fltask.controller;

import com.qczy.common.result.Result;
import com.qczy.fltask.model.dto.FlTaskCreateRequest;
import com.qczy.fltask.service.FlTaskService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
@Api(tags = "Flower Tasks")
@CrossOrigin
public class FlTaskController {

    private static final Logger log = LoggerFactory.getLogger(FlTaskController.class);

    @Autowired
    private FlTaskService flTaskService;

    @PostMapping("/fl-tasks")
    @ApiOperation("Create Flower task")
    public Result<?> createTask(@RequestBody FlTaskCreateRequest request) {
        try {
            return Result.ok(flTaskService.createTask(request));
        } catch (Exception ex) {
            log.warn("Create Flower task failed", ex);
            return Result.fail(null).message(ex.getMessage());
        }
    }

    @GetMapping("/fl-tasks")
    @ApiOperation("List Flower tasks")
    public Result<?> listTasks(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String name,
            @RequestParam(defaultValue = "1") long page,
            @RequestParam(defaultValue = "10") long size
    ) {
        try {
            return Result.ok(flTaskService.listTasks(status, name, page, size));
        } catch (Exception ex) {
            log.warn("List Flower tasks failed", ex);
            return Result.fail(null).message(ex.getMessage());
        }
    }

    @GetMapping("/fl-tasks/{taskId}")
    @ApiOperation("Get Flower task detail")
    public Result<?> getTask(@PathVariable String taskId) {
        try {
            return Result.ok(flTaskService.getTask(taskId));
        } catch (Exception ex) {
            log.warn("Get Flower task failed: {}", taskId, ex);
            return Result.fail(null).message(ex.getMessage());
        }
    }

    @GetMapping("/fl-tasks/{taskId}/rounds")
    @ApiOperation("List Flower task rounds")
    public Result<?> listRounds(@PathVariable String taskId) {
        try {
            return Result.ok(flTaskService.listRounds(taskId));
        } catch (Exception ex) {
            log.warn("List Flower task rounds failed: {}", taskId, ex);
            return Result.fail(null).message(ex.getMessage());
        }
    }

    @PostMapping("/fl-tasks/{taskId}/start")
    @ApiOperation("Start Flower task")
    public Result<?> startTask(@PathVariable String taskId) {
        try {
            return Result.ok(flTaskService.startTask(taskId));
        } catch (Exception ex) {
            log.warn("Start Flower task failed: {}", taskId, ex);
            return Result.fail(null).message(ex.getMessage());
        }
    }

    @PostMapping("/fl-tasks/{taskId}/stop")
    @ApiOperation("Stop Flower task")
    public Result<?> stopTask(@PathVariable String taskId) {
        try {
            return Result.ok(flTaskService.stopTask(taskId));
        } catch (Exception ex) {
            log.warn("Stop Flower task failed: {}", taskId, ex);
            return Result.fail(null).message(ex.getMessage());
        }
    }

    @GetMapping("/fl-datasets")
    @ApiOperation("List Flower datasets")
    public Result<?> listDatasets() {
        try {
            return Result.ok(flTaskService.listDatasets());
        } catch (Exception ex) {
            log.warn("List Flower datasets failed", ex);
            return Result.fail(null).message(ex.getMessage());
        }
    }

    @GetMapping("/fl-runner/health")
    @ApiOperation("Check Flower runner health")
    public Result<?> getRunnerHealth() {
        try {
            return Result.ok(flTaskService.getRunnerHealth());
        } catch (Exception ex) {
            log.warn("Check Flower runner health failed", ex);
            return Result.fail(null).message(ex.getMessage());
        }
    }
}
