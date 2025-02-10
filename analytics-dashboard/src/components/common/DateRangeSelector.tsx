import React from 'react';
import { format, subDays, startOfMonth, endOfMonth, subMonths, subHours, endOfDay, startOfDay } from 'date-fns';

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
  const handleDayBefore = () => {
    const now = new Date();
    const yesterdayEnd = subHours(now, 24);    // 24 hours ago
    const yesterdayStart = subHours(now, 48);  // 48 hours ago
    onDateChange(yesterdayStart, yesterdayEnd);
  };

  const handleCurrentMonth = () => {
    const now = new Date();
    const firstDayOfMonth = startOfMonth(now);
    firstDayOfMonth.setHours(0, 0, 0, 0);  // Start at midnight
    onDateChange(firstDayOfMonth, now);
  };

  const handlePreviousMonth = () => {
    const now = new Date();
    const previousMonth = subMonths(now, 1);
    const firstDayOfMonth = startOfMonth(previousMonth);
    const lastDayOfMonth = endOfMonth(previousMonth);
    firstDayOfMonth.setHours(0, 0, 0, 0);      // Start at midnight
    lastDayOfMonth.setHours(23, 59, 59, 999);  // End at last millisecond
    onDateChange(firstDayOfMonth, lastDayOfMonth);
  };

  const handleLast3Months = () => {
    const now = new Date();
    const threeMonthsAgo = subDays(now, 90);  // Exactly 90 days ago
    onDateChange(threeMonthsAgo, now);
  };

  const handleLast6Months = () => {
    const now = new Date();
    const sixMonthsAgo = subDays(now, 180);  // Exactly 180 days ago
    onDateChange(sixMonthsAgo, now);
  };

  const handleLast12Months = () => {
    const now = new Date();
    const twelveMonthsAgo = subDays(now, 365);  // Exactly 365 days ago
    onDateChange(twelveMonthsAgo, now);
  };

  return (
    <div className="flex flex-col space-y-4">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <label htmlFor="start-date" className="text-sm text-gray-600">
            From
          </label>
          <input
            id="start-date"
            type="datetime-local"
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
            value={format(startDate, "yyyy-MM-dd'T'HH:mm")}
            onChange={(e) => {
              const newStart = new Date(e.target.value);
              onDateChange(newStart, endDate);
            }}
            max={format(endDate, "yyyy-MM-dd'T'HH:mm")}
          />
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="end-date" className="text-sm text-gray-600">
            To
          </label>
          <input
            id="end-date"
            type="datetime-local"
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm"
            value={format(endDate, "yyyy-MM-dd'T'HH:mm")}
            onChange={(e) => {
              const newEnd = new Date(e.target.value);
              onDateChange(startDate, newEnd);
            }}
            min={format(startDate, "yyyy-MM-dd'T'HH:mm")}
            max={format(new Date(), "yyyy-MM-dd'T'HH:mm")}
          />
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          onClick={handleDayBefore}
          className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
        >
          Day Before
        </button>
        <button
          onClick={handleCurrentMonth}
          className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
        >
          Current Month
        </button>
        <button
          onClick={handlePreviousMonth}
          className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
        >
          Previous Month
        </button>
        <button
          onClick={handleLast3Months}
          className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
        >
          Last 3 Months
        </button>
        <button
          onClick={handleLast6Months}
          className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
        >
          Last 6 Months
        </button>
        <button
          onClick={handleLast12Months}
          className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
        >
          Last 12 Months
        </button>
      </div>
    </div>
  );
};

export default DateRangeSelector;