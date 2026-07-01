'use client';

import ConversationNode from './ConversationNode';
import DecisionNode from './DecisionNode';
import ToolNode from './ToolNode';
import TransferCallNode from './TransferCallNode';
import EndCallNode from './EndCallNode';
import ApiRequestNode from './ApiRequestNode';

export { NodeActionsContext, type NodeActions } from './nodeShared';

export const nodeTypes = {
  conversation: ConversationNode,
  decision: DecisionNode,
  tool: ToolNode,
  transferCall: TransferCallNode,
  endCall: EndCallNode,
  apiRequest: ApiRequestNode,
};
