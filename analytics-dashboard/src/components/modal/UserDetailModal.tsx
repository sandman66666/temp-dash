import React, { useState, useEffect } from 'react'
import { fetchUserEvents, UserEvent, UserEventsResponse } from '../../services/metricService'

interface UserDetailModalProps {
  metricId: string
  onClose: () => void
}

const UserDetailModal: React.FC<UserDetailModalProps> = ({ metricId, onClose }) => {
  const [data, setData] = useState<UserEvent[] | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string>('')
  const [startDate, setStartDate] = useState<Date>(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)) // 30 days ago
  const [endDate, setEndDate] = useState<Date>(new Date())

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        setError('')
        const response: UserEventsResponse = await fetchUserEvents(metricId, startDate, endDate)
        console.log('Fetched user events:', response)
        if (response.status === 'success' && Array.isArray(response.data)) {
          setData(response.data)
        } else {
          throw new Error('Invalid response format')
        }
      } catch (err: any) {
        console.error('Error fetching user events:', err)
        setError('Error fetching data: ' + (err.message || 'Unknown error'))
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [metricId, startDate, endDate])

  const handleDateChange = (isStartDate: boolean) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const date = new Date(e.target.value)
    if (isStartDate) {
      setStartDate(date)
    } else {
      setEndDate(date)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
      <div className="bg-white p-6 rounded-lg max-w-3xl w-full max-h-[80vh] overflow-auto">
        <button onClick={onClose} className="text-red-500 mb-4">Close</button>
        <div className="mb-4">
          <label className="mr-2">Start Date:</label>
          <input
            type="date"
            value={startDate.toISOString().split('T')[0]}
            onChange={handleDateChange(true)}
            className="border rounded p-1"
          />
          <label className="mx-2">End Date:</label>
          <input
            type="date"
            value={endDate.toISOString().split('T')[0]}
            onChange={handleDateChange(false)}
            className="border rounded p-1"
          />
        </div>
        {loading && <div>Loading data...</div>}
        {error && <div className="text-red-500">{error}</div>}
        {!loading && !error && data && (
          <div>
            <h2 className="text-xl font-bold mb-4">User Events for {metricId}</h2>
            {data.length === 0 ? (
              <p>No events found for this user in the selected date range.</p>
            ) : (
              <ul className="space-y-4">
                {data.map((event, index) => (
                  <li key={index} className="border-b pb-2">
                    <p><strong>Event Name:</strong> {event.event_name}</p>
                    <p><strong>Timestamp:</strong> {new Date(event.timestamp).toLocaleString()}</p>
                    {event.flow_id && <p><strong>Flow ID:</strong> {event.flow_id}</p>}
                    <details>
                      <summary className="cursor-pointer text-blue-500">Event Details</summary>
                      <pre className="text-sm bg-gray-100 p-2 mt-2 rounded">
                        {JSON.stringify(event, null, 2)}
                      </pre>
                    </details>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default UserDetailModal