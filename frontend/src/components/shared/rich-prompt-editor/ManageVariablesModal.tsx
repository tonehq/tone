'use client';

import type { Editor } from '@tiptap/react';
import { Plus, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import CustomButton from '@/components/shared/CustomButton';
import CustomModal from '@/components/shared/CustomModal';
import TextInput from '@/components/shared/TextInput';
import { isKnownPromptVariable } from '@/constants/promptVariables';
import { cn } from '@/utils/cn';

import {
  type CustomVariable,
  getCustomVariables,
  insertCustomVariable,
  removeCustomVariable,
  sanitizeVariableDefault,
  sanitizeVariableKey,
  updateCustomVariableDefault,
} from './editorVariables';

interface ManageVariablesModalProps {
  editor: Editor | null;
  open: boolean;
  onClose: () => void;
}

/**
 * Create, edit, delete and (re)insert custom variables. Custom variables are stored
 * inline in the prompt as `{{key|default}}` chips — this panel reads and mutates the
 * editor document directly; there is no separate persistence.
 */
export default function ManageVariablesModal({ editor, open, onClose }: ManageVariablesModalProps) {
  const [vars, setVars] = useState<CustomVariable[]>([]);
  const [newKey, setNewKey] = useState('');
  const [newDefault, setNewDefault] = useState('');
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    if (editor) setVars(getCustomVariables(editor));
  }, [editor]);

  useEffect(() => {
    if (open) {
      reload();
      setNewKey('');
      setNewDefault('');
      setError(null);
    }
  }, [open, reload]);

  const handleAdd = () => {
    if (!editor) return;
    const key = sanitizeVariableKey(newKey.trim());
    if (!key) {
      setError('Enter a variable name (letters, numbers, underscore).');
      return;
    }
    if (isKnownPromptVariable(key)) {
      setError(`“${key}” is a built-in variable. Pick another name.`);
      return;
    }
    if (vars.some((v) => v.key === key)) {
      setError(`“${key}” already exists.`);
      return;
    }
    insertCustomVariable(editor, key, sanitizeVariableDefault(newDefault));
    setNewKey('');
    setNewDefault('');
    setError(null);
    reload();
  };

  const handleDefaultChange = (key: string, raw: string) => {
    const next = sanitizeVariableDefault(raw);
    setVars((prev) => prev.map((v) => (v.key === key ? { ...v, default: next } : v)));
  };

  const commitDefault = (key: string, value: string) => {
    if (editor) updateCustomVariableDefault(editor, key, value);
  };

  const handleDelete = (key: string) => {
    if (!editor) return;
    removeCustomVariable(editor, key);
    reload();
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Custom variables"
      description="Define your own variables with a default value. They're stored in the prompt as {{name}} and replaced with the default at runtime."
      width="sm:max-w-xl"
      footer={
        <CustomButton type="default" onClick={onClose}>
          Done
        </CustomButton>
      }
    >
      <div className="flex flex-col gap-4">
        {/* Add form */}
        <div className="rounded-lg border border-border/70 p-3">
          <div className="flex items-end gap-2">
            <div className="w-40 shrink-0">
              <TextInput
                name="new_variable_key"
                label="Name"
                placeholder="discount_code"
                value={newKey}
                onChange={(e) => setNewKey(sanitizeVariableKey(e.target.value))}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAdd();
                  }
                }}
              />
            </div>
            <div className="flex-1">
              <TextInput
                name="new_variable_default"
                label="Default value"
                placeholder="SAVE10"
                value={newDefault}
                onChange={(e) => setNewDefault(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAdd();
                  }
                }}
              />
            </div>
            <CustomButton
              type="primary"
              icon={<Plus className="size-3.5" />}
              onClick={handleAdd}
              disabled={!editor}
            >
              Add
            </CustomButton>
          </div>
          {error && <p className="mt-1.5 text-xs text-destructive">{error}</p>}
        </div>

        {/* Existing custom variables */}
        {vars.length === 0 ? (
          <p className="px-1 py-2 text-sm text-muted-foreground">
            No custom variables yet. Add one above — it&apos;s inserted into the prompt and
            reusable.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {vars.map((v) => (
              <div key={v.key} className="flex items-center gap-2">
                <span
                  className={cn(
                    'inline-flex shrink-0 items-center rounded-md border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 font-mono text-xs text-amber-700 dark:text-amber-300',
                  )}
                  title={`{{${v.key}}}`}
                >
                  {`{{${v.key}}}`}
                </span>
                <div className="flex-1">
                  <TextInput
                    name={`var_default_${v.key}`}
                    placeholder="Default value"
                    value={v.default}
                    onChange={(e) => handleDefaultChange(v.key, e.target.value)}
                    onBlur={(e) => commitDefault(v.key, e.target.value)}
                  />
                </div>
                <CustomButton
                  type="text"
                  size="sm"
                  onClick={() => editor && insertCustomVariable(editor, v.key, v.default)}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  Insert
                </CustomButton>
                <CustomButton
                  type="text"
                  size="sm"
                  icon={<Trash2 className="size-3.5" />}
                  onClick={() => handleDelete(v.key)}
                  className="text-muted-foreground hover:text-destructive"
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </CustomModal>
  );
}
