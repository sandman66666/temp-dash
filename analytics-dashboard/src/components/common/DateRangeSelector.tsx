import React from 'react';
import { format, subDays, startOfMonth, endOfMonth, subMonths } from 'date-fns';

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
  const handleYesterday = () => {
    const yesterday = subDays(new Date(), 1);
    onDateChange(yesterday, yesterday);
  };

  const handleCurrentMonth = () => {
    const now = new Date();
    onDateChange(startOfMonth(now), now);
  };

  const handlePreviousMonth = () => {
    const now = new Date();
    const previousMonth = subMonths(now, 1);
    onDateChange(startOfMonth(previousMonth), endOfMonth(previousMonth));
  };

  const handlePrevious3Months = () => {
    const now = new Date();
    const threeMonthsAgo = subMonths(now, 3);
    onDateChange(threeMonthsAgo, now);
  };

  const handlePrevious6Months = () => {
    const now = new Date();
    const sixMonthsAgo = subMonths(now, 6);
    onDateChange(sixMonthsAgo, now);
  };

  const handlePrevious12Months = () => {
    const now = new Date();
    const twelveMonthsAgo = subMonths(now, 12);
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
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          onClick={handleYesterday}
          className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
        >
          Yesterday
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
          onClick={handlePrevious3Months}
          className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
        >
          Last 3 Months
        </button>
        <button
          onClick={handlePrevious6Months}
          className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
        >
          Last 6 Months
        </button>
        <button
          onClick={handlePrevious12Months}
          className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
        >
          Last 12 Months
        </button>
      </div>
    </div>
  );
};

export default DateRangeSelector;