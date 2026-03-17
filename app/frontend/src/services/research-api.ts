const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ResearchPipelineRequest {
  source: string;
  model_name?: string;
  model_provider?: string;
  skip_video?: boolean;
}

export interface ResearchStageUpdate {
  agent: string;
  status: string;
  analysis?: string;
}

export interface ResearchPipelineCallbacks {
  onStart: () => void;
  onProgress: (update: ResearchStageUpdate) => void;
  onComplete: (data: any) => void;
  onError: (message: string) => void;
}

export function runResearchPipeline(
  request: ResearchPipelineRequest,
  callbacks: ResearchPipelineCallbacks
): () => void {
  const controller = new AbortController();

  fetch(`${API_BASE_URL}/research-pipeline/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal: controller.signal,
  })
    .then(response => {
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const reader = response.body?.getReader();
      if (!reader) throw new Error('Failed to get response reader');

      const decoder = new TextDecoder();
      let buffer = '';

      const processStream = async () => {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const events = buffer.split('\n\n');
            buffer = events.pop() || '';

            for (const eventText of events) {
              if (!eventText.trim()) continue;
              try {
                const eventTypeMatch = eventText.match(/^event: (.+)$/m);
                const dataMatch = eventText.match(/^data: (.+)$/m);

                if (eventTypeMatch && dataMatch) {
                  const eventType = eventTypeMatch[1];
                  const eventData = JSON.parse(dataMatch[1]);

                  switch (eventType) {
                    case 'start':
                      callbacks.onStart();
                      break;
                    case 'progress':
                      callbacks.onProgress({
                        agent: eventData.agent,
                        status: eventData.status,
                        analysis: eventData.analysis,
                      });
                      break;
                    case 'complete':
                      callbacks.onComplete(eventData.data);
                      break;
                    case 'error':
                      callbacks.onError(eventData.message);
                      break;
                  }
                }
              } catch (err) {
                console.error('Error parsing SSE event:', err);
              }
            }
          }
        } catch (error: any) {
          if (error.name !== 'AbortError') {
            callbacks.onError(error.message || 'Connection error');
          }
        }
      };

      processStream();
    })
    .catch((error: any) => {
      if (error.name !== 'AbortError') {
        callbacks.onError(error.message || 'Connection failed');
      }
    });

  return () => controller.abort();
}
