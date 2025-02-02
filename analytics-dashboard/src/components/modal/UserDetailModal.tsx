// analytics-dashboard/src/components/modal/UserDetailModal.tsx
import React, { useState, useEffect } from 'react'
import axios from 'axios'

interface UserDetailModalProps {
  metricId: string
  onClose: () => void
}

const UserDetailModal: React.FC<UserDetailModalProps> = ({ metricId, onClose }) => {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string>('')

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        setError('')
        // Use VITE_API_URL from environment variables (or fallback to localhost:5001)
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5001'
        // Call the backend endpoint /getTaskResults with the metricId parameter.
        // (Ensure your backend is set up to handle this parameter appropriately.)
        const response = await axios.get(`${apiUrl}/getTaskResults`, { params: { metricId } })
        console.log('Fetched data:', response.data)
        setData(response.data)
      } catch (err: any) {
        console.error('Error fetching modal data:', err)
        setError('Error fetching data')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [metricId])

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
      <div className="bg-white p-6 rounded-lg max-w-3xl w-full">
        <button onClick={onClose} className="text-red-500 mb-4">Close</button>
        {loading && <div>Loading data...</div>}
        {error && <div className="text-red-500">{error}</div>}
        {!loading && !error && data && (
          <div>
            <h2 className="text-xl font-bold mb-4">Drill‑Down Data for {metricId}</h2>
            <pre className="text-sm bg-gray-100 p-4 rounded">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

export default UserDetailModal