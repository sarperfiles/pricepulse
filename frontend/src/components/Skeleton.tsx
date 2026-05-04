interface SkeletonProps {
  width?: string;
  height?: string;
  rounded?: string;
  className?: string;
}

export function Skeleton({ width, height, rounded = 'rounded', className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-slate-800 ${rounded} ${className}`}
      style={{ width, height }}
    />
  );
}

export function ProductTableSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Skeleton width="120px" height="28px" rounded="rounded-md" />
          <Skeleton width="160px" height="16px" rounded="rounded-md" className="mt-2" />
        </div>
        <Skeleton width="130px" height="38px" rounded="rounded-lg" />
      </div>
      <Skeleton width="100%" height="42px" rounded="rounded-lg" />
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-800 flex gap-4">
          <Skeleton width="25%" height="12px" rounded="rounded" />
          <Skeleton width="25%" height="12px" rounded="rounded" />
          <Skeleton width="15%" height="12px" rounded="rounded" />
          <Skeleton width="15%" height="12px" rounded="rounded" />
          <Skeleton width="10%" height="12px" rounded="rounded" />
        </div>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="px-5 py-4 border-b border-slate-800 flex items-center gap-4">
            <Skeleton width="25%" height="16px" rounded="rounded" />
            <Skeleton width="25%" height="14px" rounded="rounded" />
            <Skeleton width="15%" height="16px" rounded="rounded" />
            <Skeleton width="15%" height="14px" rounded="rounded" />
            <Skeleton width="60px" height="22px" rounded="rounded-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function DetailPageSkeleton() {
  let numCards = 4;
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <Skeleton width="140px" height="16px" rounded="rounded" />
          <Skeleton width="300px" height="28px" rounded="rounded-md" className="mt-3" />
          <Skeleton width="250px" height="14px" rounded="rounded" className="mt-2" />
        </div>
        <div className="flex gap-2">
          <Skeleton width="120px" height="38px" rounded="rounded-lg" />
          <Skeleton width="90px" height="38px" rounded="rounded-lg" />
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {Array.from({ length: numCards }).map((_, i) => (
          <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <Skeleton width="80px" height="12px" rounded="rounded" />
            <Skeleton width="100px" height="32px" rounded="rounded-md" className="mt-2" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-slate-900/50 border border-slate-800/50 rounded-lg p-4">
            <Skeleton width="80px" height="10px" rounded="rounded" />
            <Skeleton width="100px" height="16px" rounded="rounded" className="mt-2" />
          </div>
        ))}
      </div>
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <Skeleton width="140px" height="20px" rounded="rounded-md" className="mb-4" />
        <Skeleton width="100%" height="250px" rounded="rounded-lg" />
      </div>
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Skeleton width="140px" height="28px" rounded="rounded-md" />
          <Skeleton width="220px" height="16px" rounded="rounded" className="mt-2" />
        </div>
        <Skeleton width="120px" height="38px" rounded="rounded-lg" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center gap-3 mb-3">
              <Skeleton width="34px" height="34px" rounded="rounded-lg" />
              <Skeleton width="100px" height="14px" rounded="rounded" />
            </div>
            <Skeleton width="60px" height="32px" rounded="rounded-md" />
            <Skeleton width="50px" height="12px" rounded="rounded" className="mt-2" />
          </div>
        ))}
      </div>
      {/* TODO: maybe add chart skeleton too */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl">
        <div className="p-5 border-b border-slate-800">
          <Skeleton width="160px" height="20px" rounded="rounded-md" />
        </div>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center justify-between px-5 py-4 border-b border-slate-800 last:border-0">
            <div className="flex-1">
              <Skeleton width="200px" height="16px" rounded="rounded" />
              <Skeleton width="120px" height="12px" rounded="rounded" className="mt-1" />
            </div>
            <Skeleton width="80px" height="20px" rounded="rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}
