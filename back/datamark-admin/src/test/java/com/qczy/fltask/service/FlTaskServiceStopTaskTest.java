package com.qczy.fltask.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.qczy.fltask.mapper.FlTaskMapper;
import com.qczy.fltask.mapper.FlTaskRoundMetricMapper;
import com.qczy.fltask.model.dto.FlTaskView;
import com.qczy.fltask.model.entity.FlTaskEntity;
import com.qczy.fltask.runner.FlowerRunnerClient;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class FlTaskServiceStopTaskTest {

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

    private FlTaskEntity runningTask;

    @BeforeEach
    void setUp() {
        runningTask = buildTask("RUNNING");
        when(flTaskMapper.selectOne(any())).thenAnswer(invocation -> runningTask);
        when(flTaskMapper.updateById(any(FlTaskEntity.class))).thenReturn(1);
    }

    @Test
    void shouldStopRunnerTaskWhenTargetIsActuallyActive() {
        when(flowerRunnerClient.getHealth())
                .thenReturn(health(true, TASK_ID))
                .thenReturn(health(false, null));
        when(flowerRunnerClient.stopTask(TASK_ID)).thenReturn(Collections.<String, Object>emptyMap());

        FlTaskView view = flTaskService.stopTask(TASK_ID);

        assertEquals("STOPPED", view.getStatus());
        assertNotNull(view.getFinishedAt());
        verify(flowerRunnerClient).stopTask(TASK_ID);
        verify(flTaskMapper).updateById(runningTask);
    }

    @Test
    void shouldCollapseStaleRunningTaskWhenRunnerIsAlreadyIdle() {
        when(flowerRunnerClient.getHealth()).thenReturn(health(false, null));

        FlTaskView view = flTaskService.stopTask(TASK_ID);

        assertEquals("STOPPED", view.getStatus());
        assertNotNull(view.getFinishedAt());
        verify(flowerRunnerClient, never()).stopTask(anyString());
        verify(flTaskMapper).updateById(runningTask);
    }

    @Test
    void shouldNotStopOtherActiveTaskAndStillCollapseTargetToStopped() {
        when(flowerRunnerClient.getHealth()).thenReturn(health(true, "fl_other_002"));

        FlTaskView view = flTaskService.stopTask(TASK_ID);

        assertEquals("STOPPED", view.getStatus());
        verify(flowerRunnerClient, never()).stopTask(anyString());
        verify(flTaskMapper).updateById(runningTask);
    }

    @Test
    void shouldFailWhenRunnerHealthCannotBeRead() {
        when(flowerRunnerClient.getHealth()).thenThrow(new IllegalStateException("connect failed"));

        IllegalStateException exception = assertThrows(
                IllegalStateException.class,
                () -> flTaskService.stopTask(TASK_ID)
        );

        assertTrue(exception.getMessage().contains("Flower runner is unavailable"));
        verify(flowerRunnerClient, never()).stopTask(anyString());
        verify(flTaskMapper, never()).updateById(any(FlTaskEntity.class));
    }

    @Test
    void shouldKeepCompletedTaskUnchangedWhenItIsNotRunning() {
        FlTaskEntity completedTask = buildTask("COMPLETED");
        completedTask.setFinishedAt(LocalDateTime.of(2026, 3, 19, 12, 0));
        when(flTaskMapper.selectOne(any())).thenReturn(completedTask);
        when(flowerRunnerClient.getHealth()).thenReturn(health(false, null));

        FlTaskView view = flTaskService.stopTask(TASK_ID);

        assertEquals("COMPLETED", view.getStatus());
        verify(flowerRunnerClient, never()).stopTask(anyString());
        verify(flTaskMapper, never()).updateById(any(FlTaskEntity.class));
    }

    private FlTaskEntity buildTask(String status) {
        FlTaskEntity task = new FlTaskEntity();
        task.setId(1L);
        task.setTaskId(TASK_ID);
        task.setName("demo");
        task.setStatus(status);
        task.setTaskType("detection");
        task.setNumRounds(5);
        task.setCurrentRound(2);
        task.setCreatedAt(LocalDateTime.of(2026, 3, 19, 10, 0));
        task.setStartedAt(LocalDateTime.of(2026, 3, 19, 10, 5));
        return task;
    }

    private Map<String, Object> health(boolean running, String activeTaskId) {
        Map<String, Object> payload = new LinkedHashMap<String, Object>();
        payload.put("ok", true);
        payload.put("running", running);
        payload.put("activeTaskId", activeTaskId);
        return payload;
    }
}
