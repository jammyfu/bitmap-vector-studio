import React, { useState } from 'react';
import type { ConversionTask } from '../types';

interface QueueBarProps {
  tasks: ConversionTask[];
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  onRemoveTask?: (id: string) => void;
  onClearCompleted?: () => void;
  onStartAll?: () => void;
}

const statusMap: Record<ConversionTask['status'], { label: string; color: string; bg: string }> = {
  pending: { label: '待处理', color: '#6b6b6b', bg: '#f5f5f7' },
  running: { label: '转换中', color: '#c45c26', bg: 'rgba(196, 92, 38, 0.08)' },
  completed: { label: '完成', color: '#34c759', bg: 'rgba(52, 199, 89, 0.08)' },
  failed: { label: '失败', color: '#ff3b30', bg: 'rgba(255, 59, 48, 0.08)' },
  cancelled: { label: '已取消', color: '#a1a1a6', bg: '#f5f5f7' },
};

const QueueBar: React.FC<QueueBarProps> = ({
  tasks,
  isExpanded: controlledExpanded,
  onToggleExpand,
  onRemoveTask,
  onClearCompleted,
  onStartAll,
}) => {
  const [internalExpanded, setInternalExpanded] = useState(false);
  const expanded = controlledExpanded !== undefined ? controlledExpanded : internalExpanded;
  const toggle = onToggleExpand || (() => setInternalExpanded((v) => !v));

  const pendingCount = tasks.filter((t) => t.status === 'pending').length;
  const runningCount = tasks.filter((t) => t.status === 'running').length;
  const completedCount = tasks.filter((t) => t.status === 'completed').length;

  const activeCount = pendingCount + runningCount;

  return (
    <div
      style={{
        borderTop: '1px solid #e5e3df',
        background: '#faf9f7',
        flexShrink: 0,
        overflow: 'hidden',
        transition: 'max-height 0.3s ease',
        maxHeight: expanded ? 200 : 40,
      }}
    >
      {/* Collapsed Header */}
      <button
        onClick={toggle}
        style={{
          width: '100%',
          height: 40,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          background: 'transparent',
          border: 'none',
          color: '#6b6b6b',
          fontSize: 13,
          cursor: 'pointer',
          fontFamily: 'inherit',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span>📁</span>
          <span>
            {tasks.length === 0
              ? '队列为空'
              : `${activeCount > 0 ? `${activeCount}个文件待处理` : `${completedCount}个文件已完成`}`}
          </span>
        </span>
        <span
          style={{
            display: 'inline-block',
            transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.3s ease',
          }}
        >
          ▲
        </span>
      </button>

      {/* Expanded Content */}
      <div
        style={{
          height: 160,
          overflow: 'auto',
          padding: '0 16px 8px',
        }}
      >
        {tasks.length === 0 ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: 80,
              color: '#a1a1a6',
              fontSize: 13,
            }}
          >
            暂无文件，拖拽图片到画布添加
          </div>
        ) : (
          <>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 80px 1fr 60px',
                gap: 8,
                padding: '6px 8px',
                fontSize: 11,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                color: '#6b6b6b',
                borderBottom: '1px solid #e5e3df',
              }}
            >
              <span>文件名</span>
              <span>状态</span>
              <span>进度</span>
              <span style={{ textAlign: 'right' }}>操作</span>
            </div>
            {tasks.map((task) => {
              const status = statusMap[task.status];
              return (
                <div
                  key={task.id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 80px 1fr 60px',
                    gap: 8,
                    alignItems: 'center',
                    padding: '8px',
                    borderRadius: 6,
                    background: status.bg,
                    marginTop: 4,
                    height: 40,
                  }}
                >
                  <span
                    style={{
                      fontSize: 13,
                      color: '#1a1a1a',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                    title={task.fileName}
                  >
                    {task.fileName}
                  </span>
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: 500,
                      color: status.color,
                    }}
                  >
                    {status.label}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div
                      style={{
                        flex: 1,
                        height: 4,
                        background: 'rgba(0,0,0,0.06)',
                        borderRadius: 2,
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          height: '100%',
                          width: `${task.progress}%`,
                          background: status.color,
                          borderRadius: 2,
                          transition: 'width 0.3s ease',
                        }}
                      />
                    </div>
                    <span
                      style={{
                        fontSize: 11,
                        fontVariantNumeric: 'tabular-nums',
                        color: '#6b6b6b',
                        minWidth: 28,
                      }}
                    >
                      {task.progress}%
                    </span>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <button
                      onClick={() => onRemoveTask?.(task.id)}
                      style={{
                        padding: '2px 8px',
                        borderRadius: 4,
                        border: 'none',
                        background: 'transparent',
                        color: '#6b6b6b',
                        fontSize: 12,
                        cursor: 'pointer',
                        fontFamily: 'inherit',
                      }}
                      title="删除"
                    >
                      🗑
                    </button>
                  </div>
                </div>
              );
            })}

            {/* Bottom actions */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: 8,
                marginTop: 8,
                paddingTop: 8,
                borderTop: '1px solid #e5e3df',
              }}
            >
              <button
                onClick={onClearCompleted}
                style={{
                  padding: '4px 10px',
                  borderRadius: 6,
                  border: '1px solid #e5e3df',
                  background: '#ffffff',
                  color: '#6b6b6b',
                  fontSize: 12,
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                }}
              >
                清空已完成
              </button>
              <button
                onClick={onStartAll}
                style={{
                  padding: '4px 10px',
                  borderRadius: 6,
                  border: '1px solid #c45c26',
                  background: '#c45c26',
                  color: '#ffffff',
                  fontSize: 12,
                  fontWeight: 500,
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                }}
              >
                全部开始
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default QueueBar;
