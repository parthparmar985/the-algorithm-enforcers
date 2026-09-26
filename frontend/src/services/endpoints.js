export const backendUrl = (import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000').replace(/\/$/, '');
export const alertsUrl = backendUrl.replace(/^http/, 'ws') + '/ws/alerts';

export function connectAlerts(onMessage) {
  let socket;
  let timer;
  let stopped = false;
  let attempt = 0;
  function connect() {
    socket = new WebSocket(alertsUrl);
    socket.onopen = () => { attempt = 0; };
    socket.onmessage = onMessage;
    socket.onerror = () => socket.close();
    socket.onclose = () => {
      if (!stopped) timer = setTimeout(connect, Math.min(30000, 1000 * 2 ** attempt++));
    };
  }
  connect();
  return () => { stopped = true; clearTimeout(timer); socket.close(); };
}
