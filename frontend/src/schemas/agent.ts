import { z } from 'zod';

export const agentGeneralSchema = z.object({
  name: z.string().min(1, 'Please enter a name for your agent'),
});

export type AgentGeneralFormData = z.infer<typeof agentGeneralSchema>;
