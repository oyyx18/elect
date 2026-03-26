package com.qczy.fltask.runner;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestTemplate;

import java.util.Collections;
import java.util.List;
import java.util.Map;

@Component
public class FlowerRunnerClient {

    private static final Logger log = LoggerFactory.getLogger(FlowerRunnerClient.class);

    @Value("${flower.runner.base-url:http://127.0.0.1:9000}")
    private String baseUrl;

    @Autowired
    private RestTemplate restTemplate;

    public Map<String, Object> createTask(Map<String, Object> payload) {
        return post("/runner/tasks", payload);
    }

    public Map<String, Object> getHealth() {
        return get("/health");
    }

    public Map<String, Object> getTaskStatus(String taskId) {
        return get("/runner/tasks/" + taskId);
    }

    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> listDatasets() {
        Map<String, Object> response = get("/runner/datasets");
        Object items = response.get("items");
        if (items instanceof List) {
            return (List<Map<String, Object>>) items;
        }
        return Collections.emptyList();
    }

    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> getTaskRounds(String taskId, int afterRound) {
        Map<String, Object> response = get("/runner/tasks/" + taskId + "/rounds?afterRound=" + afterRound);
        Object items = response.get("items");
        if (items instanceof List) {
            return (List<Map<String, Object>>) items;
        }
        return Collections.emptyList();
    }

    public Map<String, Object> stopTask(String taskId) {
        return post("/runner/tasks/" + taskId + "/stop", Collections.emptyMap());
    }

    private String buildUrl(String path) {
        if (baseUrl.endsWith("/")) {
            return baseUrl.substring(0, baseUrl.length() - 1) + path;
        }
        return baseUrl + path;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> get(String path) {
        try {
            ResponseEntity<Map> response = restTemplate.getForEntity(buildUrl(path), Map.class);
            return response.getBody() != null ? response.getBody() : Collections.emptyMap();
        } catch (HttpStatusCodeException ex) {
            log.warn("Runner GET {} failed: {}", path, ex.getResponseBodyAsString());
            throw new IllegalStateException(ex.getResponseBodyAsString(), ex);
        } catch (Exception ex) {
            log.warn("Runner GET {} failed", path, ex);
            throw new IllegalStateException("Failed to connect to Flower runner " + buildUrl(path) + ": " + ex.getMessage(), ex);
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> post(String path, Map<String, Object> payload) {
        try {
            HttpEntity<Map<String, Object>> entity = new HttpEntity<Map<String, Object>>(payload);
            ResponseEntity<Map> response = restTemplate.exchange(buildUrl(path), HttpMethod.POST, entity, Map.class);
            return response.getBody() != null ? response.getBody() : Collections.emptyMap();
        } catch (HttpStatusCodeException ex) {
            log.warn("Runner POST {} failed: {}", path, ex.getResponseBodyAsString());
            throw new IllegalStateException(ex.getResponseBodyAsString(), ex);
        } catch (Exception ex) {
            log.warn("Runner POST {} failed", path, ex);
            throw new IllegalStateException("Failed to connect to Flower runner " + buildUrl(path) + ": " + ex.getMessage(), ex);
        }
    }
}
