const SkeletonNode = ({ level = 0, childCount = 0 }) => {
  const widths = {
    role: 'w-60',
    category: 'w-48',
    skill: 'w-44',
    subskill: 'w-40',
  };

  const levels = ['role', 'category', 'skill', 'subskill'];
  const currentLevel = levels[Math.min(level, levels.length - 1)];

  return (
    <div className="flex flex-col items-center">
      <div className={`${widths[currentLevel]} animate-pulse`}>
        <div
          className={`rounded-lg p-4 ${
            level === 0
              ? 'bg-gradient-to-r from-blue-300 to-blue-400 h-20'
              : 'bg-slate-200 h-16'
          }`}
        >
          <div className="h-4 bg-white/30 rounded w-3/4 mb-2" />
          {level > 0 && <div className="h-3 bg-white/20 rounded w-1/2" />}
        </div>
      </div>

      {childCount > 0 && (
        <div className="flex gap-4 mt-6">
          {Array.from({ length: Math.min(childCount, 3) }).map((_, i) => (
            <SkeletonNode key={i} level={level + 1} childCount={level < 2 ? 2 : 0} />
          ))}
        </div>
      )}
    </div>
  );
};

const TreeSkeleton = () => {
  return (
    <div className="flex flex-col items-center py-8">
      <SkeletonNode level={0} childCount={3} />
    </div>
  );
};

export default TreeSkeleton;
