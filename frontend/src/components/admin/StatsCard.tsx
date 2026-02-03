import { ReactNode } from 'react'

interface StatsCardProps {
  title: string
  value: number | string
  icon: ReactNode
  color: 'blue' | 'green' | 'purple' | 'orange' | 'red'
  subtitle?: string
  trend?: {
    value: number
    isPositive: boolean
  }
}

const colorClasses = {
  blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400',
  green: 'bg-green-100 text-green-600 dark:bg-green-900/20 dark:text-green-400',
  purple: 'bg-purple-100 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400',
  orange: 'bg-orange-100 text-orange-600 dark:bg-orange-900/20 dark:text-orange-400',
  red: 'bg-red-100 text-red-600 dark:bg-red-900/20 dark:text-red-400',
}

export const StatsCard = ({ title, value, icon, color, subtitle, trend }: StatsCardProps) => {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>{icon}</div>
        {trend && (
          <div
            className={`text-sm font-medium ${
              trend.isPositive ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {trend.isPositive ? '↑' : '↓'} {Math.abs(trend.value)}%
          </div>
        )}
      </div>
      <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</h3>
      <div className="mt-2 flex items-baseline gap-2">
        <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </p>
        {subtitle && (
          <p className="text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>
        )}
      </div>
    </div>
  )
}
