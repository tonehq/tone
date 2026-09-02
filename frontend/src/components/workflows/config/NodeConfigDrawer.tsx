'use client';

import React from 'react';
import { Trash2 } from 'lucide-react';

import CustomDrawer from '@/components/shared/CustomDrawer';
import CustomButton from '@/components/shared/CustomButton';
import NodeConfigForm from './NodeConfigForm';
import EdgeConfigForm from './EdgeConfigForm';
import { NODE_REGISTRY } from '@/components/workflows/nodeRegistry';
import type {
  ConditionEdgeData,
  WorkflowEdge,
  WorkflowNode,
  WorkflowNodeType,
} from '@/types/workflow';

type D = Record<string, unknown>;

interface Props {
  node: WorkflowNode | null;
  edge: WorkflowEdge | null;
  /** Owning agent id when the builder is opened inside an agent editor route.
   * Enables the "Profile" group in the prompt/first-message variable picker.
   * Undefined on the standalone `/workflows/[id]` route — the group hides. */
  agentId?: string;
  onClose: () => void;
  onChangeNode: (id: string, data: D) => void;
  onChangeEdge: (id: string, data: ConditionEdgeData) => void;
  onDeleteNode: (id: string) => void;
}

const NodeConfigDrawer: React.FC<Props> = ({
  node,
  edge,
  agentId,
  onClose,
  onChangeNode,
  onChangeEdge,
  onDeleteNode,
}) => {
  const open = Boolean(node || edge);

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      side="right"
      width="w-[440px] sm:max-w-[440px]"
      title={node ? 'Node settings' : 'Edge settings'}
      footer={
        node ? (
          <div className="flex items-center justify-between">
            <CustomButton
              type="danger"
              size="sm"
              icon={<Trash2 className="h-4 w-4" />}
              onClick={() => onDeleteNode(node.id)}
              disabled={!(NODE_REGISTRY[node.type as WorkflowNodeType]?.deletable ?? true)}
            >
              Delete
            </CustomButton>
            <CustomButton type="primary" size="sm" onClick={onClose}>
              Done
            </CustomButton>
          </div>
        ) : (
          <div className="flex justify-end">
            <CustomButton type="primary" size="sm" onClick={onClose}>
              Done
            </CustomButton>
          </div>
        )
      }
    >
      {node ? (
        <NodeConfigForm node={node} agentId={agentId} onChangeNode={onChangeNode} />
      ) : edge ? (
        <EdgeConfigForm edge={edge} onChangeEdge={onChangeEdge} />
      ) : null}
    </CustomDrawer>
  );
};

export default NodeConfigDrawer;
