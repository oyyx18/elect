package com.qczy.federated.flower;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

/**
 * Remote Flower server control manager.
 *
 * Uses HTTP to control the remote Flower control API (flower_server_api.py).
 * Configuration:
 * - flower.server.remote.base-url: http://10.129.45.44:9000
 */
@Component
public class FlowerServerManager {
    private static final Logger log = LoggerFactory.getLogger(FlowerServerManager.class);

    @Value("${flower.server.remote.base-url:http://127.0.0.1:9000}")
    private String remoteBaseUrl;

    @Autowired
    private RestTemplate restTemplate;

    public boolean startServer(
            String jobId,
            String modelType,
            int numRounds,
            int minClients,
            int port,
            Double baselineAccuracy,
            Double allowedDropPercent,
            String appDir
    ) {
        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("jobId", jobId);
            payload.put("modelType", modelType);
            payload.put("numRounds", numRounds);
            payload.put("minClients", minClients);
            payload.put("port", port);
            payload.put("baselineAccuracy", baselineAccuracy);
            payload.put("allowedDropPercent", allowedDropPercent);
            if (appDir != null ) {
                payload.put("appDir", appDir);
            }

            ResponseEntity<Map> response = restTemplate.postForEntity(
                    remoteBaseUrl + "/start",
                    payload,
                    Map.class
            );
            Object started = response.getBody() != null ? response.getBody().get("started") : null;
            boolean ok = Boolean.TRUE.equals(started);
            if (ok) {
                log.info("Remote Flower server started for job: {} on port: {}", jobId, port);
            } else {
                log.warn("Remote Flower start returned unexpected response for job: {}", jobId);
            }
            return ok;
        } catch (Exception e) {
            log.error("Failed to start remote Flower server for job: {}", jobId, e);
            return false;
        }
    }

    public boolean stopServer(String jobId) {
        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("jobId", jobId);
            ResponseEntity<Map> response = restTemplate.postForEntity(
                    remoteBaseUrl + "/stop",
                    payload,
                    Map.class
            );
            Object stopped = response.getBody() != null ? response.getBody().get("stopped") : null;
            boolean ok = Boolean.TRUE.equals(stopped);
            if (ok) {
                log.info("Remote Flower server stopped for job: {}", jobId);
            } else {
                log.warn("Remote Flower stop returned unexpected response for job: {}", jobId);
            }
            return ok;
        } catch (Exception e) {
            log.error("Failed to stop remote Flower server for job: {}", jobId, e);
            return false;
        }
    }

    public boolean isServerRunning(String jobId) {
        try {
            String url = remoteBaseUrl + "/status?jobId=" + jobId;
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);
            Object running = response.getBody() != null ? response.getBody().get("running") : null;
            return Boolean.TRUE.equals(running);
        } catch (Exception e) {
            log.warn("Failed to query remote Flower status for job: {}", jobId, e);
            return false;
        }
    }
}
