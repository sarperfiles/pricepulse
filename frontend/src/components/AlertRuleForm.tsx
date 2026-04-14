import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import type { AlertRule, AlertRuleCreateData } from '../types';

interface AlertRuleFormProps {
  onSubmit: (data: AlertRuleCreateData) => Promise<void>;
  onClose: () => void;
  initialData?: AlertRule;
}

const ruleTypes = [
  { value: 'price_below', label: 'Price drops below' },
  { value: 'price_above', label: 'Price goes above' },
  { value: 'price_change_pct', label: 'Price changes by %' },
  { value: 'price_drop', label: 'Any price drop' },
];

export default function AlertRuleForm({ onSubmit, onClose, initialData }: AlertRuleFormProps) {
  const [ruleType, setRuleType] = useState<string>(initialData?.rule_type || 'price_below');
  const [threshold, setThreshold] = useState(initialData?.threshold?.toString() || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    let thresholdNum = parseFloat(threshold);
    if (isNaN(thresholdNum) && ruleType !== 'price_drop') {
      setError('Please enter a valid threshold');
      return;
    }

    setLoading(true);
    try {
      await onSubmit({
        rule_type: ruleType,
        threshold: ruleType === 'price_drop' ? 0 : thresholdNum,
        is_active: true,
      });
      onClose();
    } catch {
      setError('Failed to save alert rule');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-md">
        <div className="flex items-center justify-between p-5 border-b border-slate-800">
          <h3 className="text-lg font-semibold text-white">
            {initialData ? 'Edit Alert Rule' : 'New Alert Rule'}
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-2 rounded-lg text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Rule Type
            </label>
            <select
              value={ruleType}
              onChange={(e) => setRuleType(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500"
            >
              {ruleTypes.map((rt) => (
                <option key={rt.value} value={rt.value}>
                  {rt.label}
                </option>
              ))}
            </select>
          </div>

          {ruleType !== 'price_drop' && (
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                {ruleType === 'price_change_pct' ? 'Percentage (%)' : 'Price ($)'}
              </label>
              <input
                type="number"
                step="0.01"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                placeholder={ruleType === 'price_change_pct' ? 'e.g. 10' : 'e.g. 29.99'}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 placeholder:text-slate-600"
              />
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Saving...' : initialData ? 'Update Rule' : 'Create Rule'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
