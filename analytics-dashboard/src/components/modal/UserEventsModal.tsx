import React, { useState, useEffect } from 'react';
import { fetchUserEvents, UserEvent, UserEventsResponse } from '../../services/metricService';

interface UserEventsModalProps {
  userId: string;
  onClose: () => void;
}

interface GroupedEvents {
  [flowId: string]: UserEvent[];
}

const UserEventsModal: React.FC<UserEventsModalProps> = ({ userId, onClose }) => {
  const [events, setEvents] = useState<UserEvent[]>([]);
  const [groupedEvents, setGroupedEvents] = useState<GroupedEvents>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [expandedFlows, setExpandedFlows] = useState<Set<string>>(new Set());
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());

  useEffect(() => {
    const loadUserEvents = async () => {
      try {
        setLoading(true);
        setError('');
        const response: UserEventsResponse = await fetchUserEvents(userId);
        if (response.status === 'success' && Array.isArray(response.data)) {
          setEvents(response.data);
          groupEventsByFlow(response.data);
        } else {
          throw new Error('Invalid response format from server');
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load user events');
        console.error('Error loading user events:', err);
      } finally {
        setLoading(false);
      }
    };

    loadUserEvents();
  }, [userId]);

  const groupEventsByFlow = (events: UserEvent[]) => {
    const grouped = events.reduce((acc: GroupedEvents, event) => {
      const flowId = event.flow_id || 'No Flow';
      if (!acc[flowId]) {
        acc[flowId] = [];
      }
      acc[flowId].push(event);
      return acc;
    }, {});

    // Sort events within each flow by timestamp
    Object.keys(grouped).forEach(flowId => {
      grouped[flowId].sort((a, b) => 
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );
    });

    setGroupedEvents(grouped);
  };

  const toggleFlow = (flowId: string) => {
    const newExpandedFlows = new Set(expandedFlows);
    if (expandedFlows.has(flowId)) {
      newExpandedFlows.delete(flowId);
    } else {
      newExpandedFlows.add(flowId);
    }
    setExpandedFlows(newExpandedFlows);
  };

  const toggleEvent = (eventId: string) => {
    const newExpandedEvents = new Set(expandedEvents);
    if (expandedEvents.has(eventId)) {
      newExpandedEvents.delete(eventId);
    } else {
      newExpandedEvents.add(eventId);
    }
    setExpandedEvents(newExpandedEvents);
  };

  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-start overflow-y-auto py-8 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 my-auto">
        <div className="p-6 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h2 className="text-2xl font-bold text-gray-900">
              User Activities
              <span className="ml-2 text-sm font-normal text-gray-500">
                {userId}
              </span>
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500 transition-colors"
              aria-label="Close"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div className="p-6">
          {loading && (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
              <p className="mt-4 text-gray-500">Loading user activities...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">Error loading activities</h3>
                  <p className="text-sm text-red-700 mt-1">{error}</p>
                </div>
              </div>
            </div>
          )}

          {!loading && !error && Object.entries(groupedEvents).length === 0 && (
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="mt-4 text-gray-500">No activities found for this user</p>
            </div>
          )}

          {!loading && !error && Object.entries(groupedEvents).map(([flowId, flowEvents]) => (
            <div key={flowId} className="mb-4 border rounded-lg overflow-hidden">
              <button
                className="w-full bg-gray-50 px-6 py-4 flex justify-between items-center hover:bg-gray-100 transition-colors"
                onClick={() => toggleFlow(flowId)}
              >
                <div className="flex items-center">
                  <h3 className="text-lg font-medium text-gray-900">
                    {flowId}
                  </h3>
                  <span className="ml-3 text-sm text-gray-500">
                    {flowEvents.length} {flowEvents.length === 1 ? 'event' : 'events'}
                  </span>
                </div>
                <svg
                  className={`h-5 w-5 text-gray-500 transform transition-transform ${
                    expandedFlows.has(flowId) ? 'rotate-180' : ''
                  }`}
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>

              {expandedFlows.has(flowId) && (
                <div className="divide-y divide-gray-200">
                  {flowEvents.map((event) => (
                    <div key={event.id} className="px-6 py-4">
                      <button
                        className="w-full flex justify-between items-center text-left"
                        onClick={() => toggleEvent(event.id)}
                      >
                        <div>
                          <p className="text-sm font-medium text-gray-900">{event.event_name}</p>
                          <p className="text-sm text-gray-500">{formatDate(event.timestamp)}</p>
                        </div>
                        <svg
                          className={`h-5 w-5 text-gray-500 transform transition-transform ${
                            expandedEvents.has(event.id) ? 'rotate-180' : ''
                          }`}
                          viewBox="0 0 20 20"
                          fill="currentColor"
                        >
                          <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      </button>

                      {expandedEvents.has(event.id) && (
                        <div className="mt-4 bg-gray-50 rounded-md p-4">
                          <pre className="text-sm text-gray-700 whitespace-pre-wrap break-words">
                            {JSON.stringify(event, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default UserEventsModal;