/**
 * Live SSE Event Stream Client for Aether-SWE Telemetry.
 */
class SSEClient {
  constructor(endpoint = "/api/events") {
    self.endpoint = endpoint;
    this.eventSource = null;
    this.handlers = [];
  }

  connect() {
    this.eventSource = new EventSource(this.endpoint);

    this.eventSource.onmessage = (e) => {
      try {
        const eventData = JSON.parse(e.data);
        this.notify(eventData);
      } catch (err) {
        // Ping or malformed payload
      }
    };

    this.eventSource.onerror = (err) => {
      console.warn("SSE connection interrupted, retrying...", err);
    };
  }

  onEvent(handler) {
    this.handlers.push(handler);
  }

  notify(eventData) {
    for (const h of this.handlers) {
      h(eventData);
    }
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}

window.sseClient = new SSEClient();
