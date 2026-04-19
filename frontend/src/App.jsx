import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [calls, setCalls] = useState([]);
  const [activeCalls, setActiveCalls] = useState([]);
  const [selectedCall, setSelectedCall] = useState(null);
  const [ws, setWs] = useState(null);

  useEffect(() => {
    // Fetch initial calls
    fetchCalls();
    
    // Setup WebSocket for real-time updates
    const websocket = new WebSocket('ws://localhost:8000/ws/dashboard');
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setActiveCalls(data.active_calls || []);
    };
    setWs(websocket);
    
    return () => {
      if (websocket) websocket.close();
    };
  }, []);

  const fetchCalls = async () => {
    try {
      const response = await fetch('/api/calls');
      const data = await response.json();
      setCalls(data);
    } catch (error) {
      console.error('Error fetching calls:', error);
    }
  };

  const fetchCallDetails = async (callId) => {
    try {
      const response = await fetch(`/api/calls/${callId}`);
      const data = await response.json();
      setSelectedCall(data);
    } catch (error) {
      console.error('Error fetching call details:', error);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Free AI Call Center Dashboard</h1>
      </header>
      
      <div className="dashboard-container">
        <div className="sidebar">
          <h2>Active Calls ({activeCalls.length})</h2>
          <div className="active-calls">
            {activeCalls.map((call, index) => (
              <div key={index} className="active-call">
                <div className="caller-id">{call.caller_id}</div>
                <div className="call-status">🟢 Active</div>
              </div>
            ))}
          </div>
          
          <h2>Recent Calls</h2>
          <div className="call-list">
            {calls.map((call) => (
              <div 
                key={call.id} 
                className="call-item"
                onClick={() => fetchCallDetails(call.id)}
              >
                <div className="caller-id">{call.caller_id}</div>
                <div className="call-time">
                  {new Date(call.start_time).toLocaleString()}
                </div>
                <div className={`call-status ${call.status}`}>
                  {call.status}
                </div>
              </div>
            ))}
          </div>
        </div>
        
        <div className="main-content">
          {selectedCall ? (
            <div className="call-details">
              <h2>Call Details</h2>
              <div className="call-info">
                <p><strong>Caller ID:</strong> {selectedCall.caller_id}</p>
                <p><strong>Start Time:</strong> {new Date(selectedCall.start_time).toLocaleString()}</p>
                {selectedCall.end_time && (
                  <p><strong>End Time:</strong> {new Date(selectedCall.end_time).toLocaleString()}</p>
                )}
                <p><strong>Status:</strong> {selectedCall.status}</p>
              </div>
              
              <h3>Conversation Transcript</h3>
              <div className="transcript">
                {selectedCall.transcript ? (
                  selectedCall.transcript.split('\n').map((line, index) => (
                    <div key={index} className={line.startsWith('Agent:') ? 'agent-message' : 'customer-message'}>
                      {line}
                    </div>
                  ))
                ) : (
                  <p>No transcript available</p>
                )}
              </div>
            </div>
          ) : (
            <div className="welcome-screen">
              <h2>Welcome to Your Free AI Call Center</h2>
              <p>Select a call from the sidebar to view details</p>
              
              <div className="stats">
                <div className="stat-card">
                  <h3>Total Calls Today</h3>
                  <div className="stat-number">{calls.filter(call => 
                    new Date(call.start_time).toDateString() === new Date().toDateString()
                  ).length}</div>
                </div>
                
                <div className="stat-card">
                  <h3>Active Calls</h3>
                  <div className="stat-number">{activeCalls.length}</div>
                </div>
                
                <div className="stat-card">
                  <h3>Completed Calls</h3>
                  <div className="stat-number">{calls.filter(call => call.status === 'completed').length}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
