import { useState, useEffect } from 'react'
import axios from 'axios'
// import io from 'socket.io-client'  // Commented out - backend uses raw WebSocket
import './App.css'

function App() {
  const [draftId, setDraftId] = useState('af521ecf-3f80-43b5-9a3c-cafa51c3b131')
  const [draft, setDraft] = useState(null)
  const [picks, setPicks] = useState([])
  const [socket, setSocket] = useState(null)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')

  // Fetch draft data
  useEffect(() => {
    const fetchDraft = async () => {
      try {
        const response = await axios.get(`/api/v1/drafts/${draftId}`)
        setDraft(response.data)
      } catch (error) {
        console.error('Error fetching draft:', error)
        setMessage('Error loading draft')
      }
    }

    fetchDraft()
  }, [draftId])

  // Fetch picks
  useEffect(() => {
    const fetchPicks = async () => {
      try {
        const response = await axios.get(`/api/v1/drafts/${draftId}/picks`)
        setPicks(response.data)
        setLoading(false)
      } catch (error) {
        console.error('Error fetching picks:', error)
        setMessage('Error loading picks')
        setLoading(false)
      }
    }

    if (draftId) {
      fetchPicks()
    }
  }, [draftId])

  // WebSocket connection (raw WebSocket - backend doesn't use socket.io)
  useEffect(() => {
    if (!draftId) return

    const wsUrl = `wss://bot-sports-empire-backend.onrender.com/ws/drafts/${draftId}`
    const newSocket = new WebSocket(wsUrl)
    setSocket(newSocket)

    newSocket.onopen = () => {
      console.log('Connected to draft room via raw WebSocket')
      setMessage('Connected to draft room')
    }

    newSocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('WebSocket message:', data)
        
        if (data.type === 'pick_made') {
          setMessage(`Pick made: ${data.pick?.player_name || 'Unknown player'}`)
          // Refresh picks
          axios.get(`/api/v1/drafts/${draftId}/picks`).then(response => {
            setPicks(response.data)
          })
        } else if (data.type === 'chat_message') {
          setMessage(`Chat: ${data.user}: ${data.text}`)
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

    newSocket.onerror = (error) => {
      console.error('WebSocket error:', error)
      setMessage('WebSocket connection error - backend uses raw WebSocket, not socket.io')
    }

    newSocket.onclose = () => {
      console.log('WebSocket disconnected')
    }

    return () => newSocket.close()
  }, [draftId])

  const assignPick = async (pickId, playerId = 'QB1') => {
    try {
      setMessage('Assigning pick...')
      
      // Try direct POST to picks endpoint
      const response = await axios.post(
        `/api/v1/drafts/${draftId}/picks`,
        {
          team_id: 'team_1',  // Hardcoded for testing
          player_id: playerId
        }
      )
      
      setMessage(`Pick assigned: ${response.data.player?.full_name || 'Unknown player'}`)
      
      // Refresh picks
      const picksResponse = await axios.get(`/api/v1/drafts/${draftId}/picks`)
      setPicks(picksResponse.data)
      
    } catch (error) {
      console.error('Error assigning pick:', error)
      const errorMsg = error.response?.data?.detail || error.message
      setMessage(`Error: ${errorMsg}`)
      
      // If error mentions draft status, try to pause draft first
      if (errorMsg.includes('IN_PROGRESS') || errorMsg.includes('status')) {
        setMessage('Draft might need to be paused. Trying alternative...')
        
        // Try to get current pick and assign to it
        try {
          const draftResponse = await axios.get(`/api/v1/drafts/${draftId}`)
          const currentPick = draftResponse.data.current_pick
          
          if (currentPick) {
            // Try assigning to current pick
            const altResponse = await axios.post(
              `/api/v1/drafts/${draftId}/picks/${currentPick}/assign`,
              { player_id: playerId }
            )
            setMessage(`Pick assigned to current pick #${currentPick}: ${altResponse.data.player_name}`)
            
            // Refresh picks
            const picksResponse = await axios.get(`/api/v1/drafts/${draftId}/picks`)
            setPicks(picksResponse.data)
          }
        } catch (altError) {
          console.error('Alternative also failed:', altError)
        }
      }
    }
  }

  if (loading) {
    return <div className="loading">Loading draft board...</div>
  }

  return (
    <div className="app">
      <header className="header">
        <h1>🏈 Bot Sports Empire - Draft Board</h1>
        {draft && (
          <div className="draft-info">
            <h2>{draft.name}</h2>
            <p>Status: <span className={`status ${draft.status}`}>{draft.status}</span></p>
            <p>Teams: {draft.team_count} | Rounds: {draft.rounds}</p>
            <p>Type: {draft.draft_type}</p>
          </div>
        )}
      </header>

      <div className="message">{message}</div>

      <div className="controls">
        <input
          type="text"
          value={draftId}
          onChange={(e) => setDraftId(e.target.value)}
          placeholder="Enter Draft ID"
        />
        <button onClick={() => window.location.reload()}>Refresh</button>
      </div>

      <div className="picks-grid">
        {picks.map((pick) => (
          <div key={pick.id} className={`pick-card ${pick.player_id ? 'taken' : 'available'}`}>
            <div className="pick-header">
              <span className="pick-number">#{pick.pick_number}</span>
              <span className="round">Round {pick.round}</span>
            </div>
            <div className="pick-body">
              <div className="team">Team: {pick.team_id || 'Unknown'}</div>
              <div className="player">
                {pick.player_name || 'Available'}
                {pick.position && <span className="position"> ({pick.position})</span>}
              </div>
              {!pick.player_id && (
                <button
                  onClick={() => assignPick(pick.id)}
                  className="assign-btn"
                >
                  Pick Mahomes
                </button>
              )}
            </div>
            {pick.is_completed && (
              <div className="pick-footer">
                <small>Completed</small>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="instructions">
        <h3>Instructions:</h3>
        <ol>
          <li>WebSocket is connected to draft room</li>
          <li>Click "Pick Mahomes" to assign Patrick Mahomes to a pick</li>
          <li>WebSocket will broadcast the pick to all connected clients</li>
          <li>Refresh page to see updated picks</li>
        </ol>
        <p>
          <strong>Test Draft ID:</strong> {draftId}
        </p>
      </div>
    </div>
  )
}

export default App