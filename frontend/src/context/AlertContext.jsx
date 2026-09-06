import { createContext, useState, useEffect, useContext } from 'react';
import { useAuth } from './AuthContext';

const AlertContext = createContext(null);

export const AlertProvider = ({ children }) => {
  const [alerts, setAlerts] = useState([]);
  const [latestAlert, setLatestAlert] = useState(null);
  const { user } = useAuth();
  
  useEffect(() => {
    if (!user) return;
    
    // Connect to WebSocket
    const ws = new WebSocket('ws://localhost:8000/ws/alerts');
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Ignore progress events in alert context
        if (data.type === 'PROGRESS') {
          return;
        }

        // Only handle alert messages
        if (data.alert_id || data.alert_type || data.type === 'ALERT') {
          setLatestAlert(data);
          setAlerts(prev => [data, ...prev]);
          
          // Auto-clear toast after 5s
          setTimeout(() => {
            setLatestAlert(curr => curr?.alert_id === data.alert_id ? null : curr);
          }, 5000);
        }
      } catch (err) {
        console.error("Alert WS Parse Error:", err);
      }
    };
    
    return () => {
      ws.close();
    };
  }, [user]);

  const clearLatest = () => setLatestAlert(null);

  return (
    <AlertContext.Provider value={{ alerts, latestAlert, clearLatest }}>
      {children}
      
      {/* Global Alert Toast */}
      {latestAlert && latestAlert.alert_type && (
        <div className="fixed bottom-4 right-4 z-50 bg-red-900 border border-red-500 text-white p-4 rounded-lg shadow-2xl max-w-sm flex flex-col gap-2 animate-bounce">
          <div className="flex justify-between items-start">
            <h4 className="font-bold text-red-200">New Alert: {latestAlert.severity || 'CRITICAL'}</h4>
            <button onClick={clearLatest} className="text-slate-300 hover:text-white text-lg leading-none">&times;</button>
          </div>
          <p className="text-sm font-medium">{(latestAlert.alert_type || '').replace('_', ' ')}</p>
          <p className="text-sm text-red-200">{latestAlert.message}</p>
        </div>
      )}
    </AlertContext.Provider>
  );
};

export const useAlert = () => useContext(AlertContext);

