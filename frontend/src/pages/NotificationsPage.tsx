import { useState, useEffect } from 'react';
import {
  Bell,
  Check,
  CheckCheck,
  AlertCircle,
  TrendingDown,
  TrendingUp,
  ArrowRight,
} from 'lucide-react';
import { getNotifications, markAsRead, markAllAsRead } from '../api/notifications';
import { useToast } from '../context/ToastContext';
import Breadcrumb from '../components/Breadcrumb';
import { formatRelativeTime } from '../utils/formatTime';
import type { Notification } from '../types';

function getDateGroup(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  let notifDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());

  if (notifDate.getTime() === today.getTime()) return 'Today';
  if (notifDate.getTime() === yesterday.getTime()) return 'Yesterday';
  return 'Older';
}

function groupNotifications(items: Notification[]): Map<string, Notification[]> {
  const groups = new Map<string, Notification[]>();
  const order = ['Today', 'Yesterday', 'Older'];
  for (const label of order) {
    const matching = items.filter((n) => getDateGroup(n.created_at) === label);
    if (matching.length > 0) groups.set(label, matching);
  }
  return groups;
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [markingAll, setMarkingAll] = useState(false);
  const { addToast } = useToast();

  useEffect(() => {
    loadNotifications();
  }, []);

  async function loadNotifications() {
    setLoading(true);
    setError('');
    try {
      const res = await getNotifications({ size: 50 });
      setNotifications(res.items);
    } catch {
      setError('Failed to load notifications');
    } finally {
      setLoading(false);
    }
  }

  async function handleMarkRead(id: number) {
    try {
      await markAsRead(String(id));
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      addToast('Marked as read', 'info');
    } catch {
      // ignore
    }
  }

  async function handleMarkAllRead() {
    setMarkingAll(true);
    try {
      await markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      addToast('All marked as read', 'info');
    } catch {
      setError('Failed to mark all as read');
    } finally {
      setMarkingAll(false);
    }
  }

  const unreadCount = notifications.filter((n) => !n.is_read).length;
  const grouped = groupNotifications(notifications);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="h-7 w-36 bg-slate-800 rounded-md animate-pulse" />
            <div className="h-4 w-48 bg-slate-800 rounded mt-2 animate-pulse" />
          </div>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="px-5 py-4 border-b border-slate-800 last:border-0 flex items-start gap-4">
              <div className="h-9 w-9 bg-slate-800 rounded-lg animate-pulse shrink-0" />
              <div className="flex-1">
                <div className="h-4 w-48 bg-slate-800 rounded animate-pulse" />
                <div className="h-3 w-72 bg-slate-800 rounded mt-2 animate-pulse" />
                <div className="h-3 w-24 bg-slate-800 rounded mt-2 animate-pulse" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Breadcrumb
        items={[
          { label: 'Home', href: '/' },
          { label: 'Notifications' },
        ]}
      />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Notifications</h1>
          <p className="text-slate-400 mt-1">
            {unreadCount > 0
              ? `${unreadCount} unread notification${unreadCount !== 1 ? 's' : ''}`
              : 'All caught up!'}
          </p>
        </div>
        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllRead}
            disabled={markingAll}
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            <CheckCheck size={16} />
            {markingAll ? 'Marking...' : 'Mark All Read'}
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {notifications.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
          <Bell size={40} className="text-slate-700 mx-auto mb-4" />
          <p className="text-slate-400">No notifications yet</p>
          <p className="text-slate-600 text-sm mt-1">
            You'll be notified when price alerts are triggered
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {Array.from(grouped.entries()).map(([group, items]) => (
            <div key={group}>
              <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-2 px-1">
                {group}
              </h3>
              <div className="bg-slate-900 border border-slate-800 rounded-xl divide-y divide-slate-800">
                {items.map((notification) => (
                  <div
                    key={notification.id}
                    className={`px-5 py-4 transition-colors ${
                      notification.is_read
                        ? 'opacity-60'
                        : 'border-l-2 border-l-emerald-500'
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      <div
                        className={`mt-0.5 p-2 rounded-lg shrink-0 ${
                          notification.is_read
                            ? 'bg-slate-800 text-slate-500'
                            : 'bg-emerald-500/15 text-emerald-400'
                        }`}
                      >
                        <Bell size={16} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3
                            className={`text-sm font-medium ${
                              notification.is_read ? 'text-slate-300' : 'text-white'
                            }`}
                          >
                            {notification.title}
                          </h3>
                          {!notification.is_read && (
                            <span className="h-2 w-2 rounded-full bg-emerald-400 shrink-0" />
                          )}
                        </div>
                        <p className="text-sm text-slate-400 mt-1">{notification.message}</p>
                        {notification.old_price !== null && notification.new_price !== null && (
                          <div className="flex items-center gap-2 mt-2">
                            <span className="text-slate-500 text-sm">
                              ${Number(notification.old_price).toFixed(2)}
                            </span>
                            <ArrowRight size={12} className="text-slate-600" />
                            <span
                              className={`text-sm font-medium ${
                                notification.new_price < notification.old_price
                                  ? 'text-emerald-400'
                                  : 'text-red-400'
                              }`}
                            >
                              ${Number(notification.new_price).toFixed(2)}
                            </span>
                            {notification.new_price < notification.old_price ? (
                              <TrendingDown size={14} className="text-emerald-400" />
                            ) : (
                              <TrendingUp size={14} className="text-red-400" />
                            )}
                          </div>
                        )}
                        <div className="flex items-center gap-3 mt-2">
                          <p className="text-xs text-slate-600">
                            {formatRelativeTime(notification.created_at)}
                            {notification.product_name && (
                              <span className="ml-2 text-slate-500">
                                {notification.product_name}
                              </span>
                            )}
                          </p>
                          {!notification.is_read && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleMarkRead(notification.id);
                              }}
                              className="flex items-center gap-1 text-xs text-slate-500 hover:text-emerald-400 transition-colors"
                            >
                              <Check size={12} />
                              Mark read
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
