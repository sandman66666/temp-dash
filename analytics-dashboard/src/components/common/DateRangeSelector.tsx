import React from 'react';
import { format } from 'date-fns';

interface DateRangeSelectorProps {
  startDate: Date;
  endDate: Date;
  onDateChange: (start: Date, end: Date) => void;
}

const DateRangeSelector: React.FC<DateRangeSelectorProps> = ({
  startDate,
  endDate,
  onDateChange,
}) => {
  return (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-2">
        <label htmlFor="start-date" className="text-sm text-gray-600">
          From
        </label>
        <input
          id="start-date"
          type="date"
          className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
          value={format(startDate, 'yyyy-MM-dd')}
          onChange={(e) => {
            const newStart = new Date(e.target.value);
            onDateChange(newStart, endDate);
          }}
          max={format(endDate, 'yyyy-MM-dd')}
        />
      </div>
      <div className="flex items-center gap-2">
        <label htmlFor="end-date" className="text-sm text-gray-600">
          To
        </label>
        <input
          id="end-date"
          type="date"
          className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
          value={format(endDate, 'yyyy-MM-dd')}
          onChange={(e) => {
            const newEnd = new Date(e.target.value);
            onDateChange(startDate, newEnd);
          }}
          min={format(startDate, 'yyyy-MM-dd')}
          max={format(new Date(), 'yyyy-MM-dd')}
        />
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => {
            const end = new Date();
            const start = new Date();
            start.setDate(end.getDate() - 7);
            onDateChange(start, end);
          }}
          className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
        >
          Last 7 days
        </button>
        <button
          onClick={() => {
            const end = new Date();
            const start = new Date();
            start.setDate(end.getDate() - 30);
            onDateChange(start, end);
          }}
          className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
        >
          Last 30 days
        </button>
      </div>
    </div>
  );
};

export default DateRangeSelector;