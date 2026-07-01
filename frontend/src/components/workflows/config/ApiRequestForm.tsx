'use client';

import React from 'react';
import { Cog, KeyRound, ListTree, Plus, Repeat2, Send } from 'lucide-react';

import CustomButton from '@/components/shared/CustomButton';
import TextInput from '@/components/shared/TextInput';
import TextAreaField from '@/components/shared/TextAreaField';
import SelectInput from '@/components/shared/SelectInput';
import CheckboxField from '@/components/shared/CheckboxField';
import Section from './ApiRequestSection';
import RemoveBtn from './ApiRequestRemoveButton';
import Empty from './ApiRequestEmptyHint';

type D = Record<string, unknown>;
type Row = Record<string, unknown>;

interface Props {
  data: D;
  patch: (p: D) => void;
}

const METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((m) => ({ value: m, label: m }));
const PROP_TYPES = ['string', 'number', 'boolean', 'object', 'array'].map((t) => ({
  value: t,
  label: t,
}));

const s = (v: unknown) => (typeof v === 'string' ? v : '');

// Stable per-row id so an encrypted value's carry-over on the backend survives a key rename
// (the server matches masked rows back to their stored secret by `_rid`, then by key name).
const rid = (): string =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `r-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;

const ApiRequestForm: React.FC<Props> = ({ data, patch }) => {
  const arr = (k: string): Row[] => (Array.isArray(data[k]) ? (data[k] as Row[]) : []);
  const setArr = (k: string, next: Row[]) => patch({ [k]: next });
  const add = (k: string, row: Row) => setArr(k, [...arr(k), row]);
  const upd = (k: string, i: number, p: Row) =>
    setArr(
      k,
      arr(k).map((r, j) => (j === i ? { ...r, ...p } : r)),
    );
  const del = (k: string, i: number) =>
    setArr(
      k,
      arr(k).filter((_, j) => j !== i),
    );

  const messages = (data.messages as D | undefined) ?? {};
  const setMsg = (key: string, v: string) => patch({ messages: { ...messages, [key]: v } });

  return (
    <div className="flex flex-col gap-3">
      <Section
        title="Base Configuration"
        description="Description, URL and HTTP method"
        icon={<Cog className="h-3.5 w-3.5" />}
        defaultOpen
      >
        <TextAreaField
          name="api-description"
          label="Description"
          rows={2}
          value={s(data.description)}
          onChange={(e) => patch({ description: e.target.value })}
          placeholder="A clear description helps the AI know when to call this."
        />
        <TextInput
          name="api-url"
          label="Request URL"
          value={s(data.url)}
          onChange={(e) => patch({ url: e.target.value })}
          placeholder="https://api.example.com/endpoint"
          className="font-mono"
          helperText="Must use https://. Supports {{variables}}."
        />
        <SelectInput
          name="api-method"
          label="HTTP method"
          options={METHODS}
          value={s(data.method) || 'GET'}
          onValueChange={(v) => patch({ method: v })}
        />
      </Section>

      <Section
        title="Authorization & Headers"
        description="Custom headers (values support {{variables}})"
        icon={<KeyRound className="h-3.5 w-3.5" />}
      >
        {arr('headers').length === 0 ? (
          <Empty>No headers. Add one for auth (e.g. Authorization).</Empty>
        ) : (
          arr('headers').map((h, i) => (
            <div key={i} className="flex items-start gap-2">
              <div className="flex flex-1 flex-col gap-2">
                <div className="flex gap-2">
                  <TextInput
                    name={`hk-${i}`}
                    value={s(h.key)}
                    onChange={(e) => upd('headers', i, { key: e.target.value })}
                    placeholder="Header name"
                    className="flex-1 font-mono"
                  />
                  <TextInput
                    name={`hv-${i}`}
                    type={h.encrypt ? 'password' : 'text'}
                    value={s(h.value)}
                    onChange={(e) =>
                      upd('headers', i, { value: e.target.value, _encrypted: false })
                    }
                    placeholder={h.encrypt && h._encrypted ? '•••••• (saved)' : 'Value or {{var}}'}
                    className="flex-1 font-mono"
                  />
                </div>
                <CheckboxField
                  id={`he-${i}`}
                  label="Encrypt this value (stored secret)"
                  checked={Boolean(h.encrypt)}
                  onCheckedChange={(c) => upd('headers', i, { encrypt: c })}
                />
              </div>
              <RemoveBtn onClick={() => del('headers', i)} label="Remove header" />
            </div>
          ))
        )}
        <CustomButton
          type="text"
          size="xs"
          icon={<Plus className="h-3.5 w-3.5" />}
          onClick={() => add('headers', { key: '', value: '', encrypt: false, _rid: rid() })}
        >
          Add Header
        </CustomButton>
      </Section>

      <Section
        title="Request Body"
        description="Properties the AI fills in and sends"
        icon={<Send className="h-3.5 w-3.5" />}
      >
        {arr('requestBody').length === 0 ? (
          <Empty>No body properties. The AI sends nothing unless you add some.</Empty>
        ) : (
          arr('requestBody').map((p, i) => (
            <div key={i} className="flex items-start gap-2">
              <div className="flex flex-1 flex-col gap-2">
                <div className="flex gap-2">
                  <TextInput
                    name={`bp-${i}`}
                    value={s(p.name)}
                    onChange={(e) => upd('requestBody', i, { name: e.target.value })}
                    placeholder="property_name"
                    className="flex-1 font-mono"
                  />
                  <div className="w-28 shrink-0">
                    <SelectInput
                      name={`bt-${i}`}
                      options={PROP_TYPES}
                      value={s(p.type) || 'string'}
                      onValueChange={(v) => upd('requestBody', i, { type: v })}
                    />
                  </div>
                </div>
                <TextInput
                  name={`bd-${i}`}
                  value={s(p.description)}
                  onChange={(e) => upd('requestBody', i, { description: e.target.value })}
                  placeholder="What the AI should put here"
                />
                <CheckboxField
                  id={`br-${i}`}
                  label="Required"
                  checked={Boolean(p.required)}
                  onCheckedChange={(c) => upd('requestBody', i, { required: c })}
                />
              </div>
              <RemoveBtn onClick={() => del('requestBody', i)} label="Remove property" />
            </div>
          ))
        )}
        <CustomButton
          type="text"
          size="xs"
          icon={<Plus className="h-3.5 w-3.5" />}
          onClick={() =>
            add('requestBody', { name: '', type: 'string', required: false, description: '' })
          }
        >
          Add Property
        </CustomButton>
      </Section>

      <Section
        title="Static Body Fields"
        description="Always-sent key/values ({{variables}} supported)"
        icon={<ListTree className="h-3.5 w-3.5" />}
      >
        {arr('staticBody').length === 0 ? (
          <Empty>No static fields configured.</Empty>
        ) : (
          arr('staticBody').map((f, i) => (
            <div key={i} className="flex items-start gap-2">
              <div className="flex flex-1 flex-col gap-2">
                <div className="flex gap-2">
                  <TextInput
                    name={`sk-${i}`}
                    value={s(f.key)}
                    onChange={(e) => upd('staticBody', i, { key: e.target.value })}
                    placeholder="field"
                    className="flex-1 font-mono"
                  />
                  <TextInput
                    name={`sv-${i}`}
                    type={f.encrypt ? 'password' : 'text'}
                    value={s(f.value)}
                    onChange={(e) =>
                      upd('staticBody', i, { value: e.target.value, _encrypted: false })
                    }
                    placeholder={f.encrypt && f._encrypted ? '•••••• (saved)' : 'value or {{var}}'}
                    className="flex-1 font-mono"
                  />
                </div>
                <CheckboxField
                  id={`se-${i}`}
                  label="Encrypt this value (stored secret)"
                  checked={Boolean(f.encrypt)}
                  onCheckedChange={(c) => upd('staticBody', i, { encrypt: c })}
                />
              </div>
              <RemoveBtn onClick={() => del('staticBody', i)} label="Remove field" />
            </div>
          ))
        )}
        <CustomButton
          type="text"
          size="xs"
          icon={<Plus className="h-3.5 w-3.5" />}
          onClick={() => add('staticBody', { key: '', value: '', encrypt: false, _rid: rid() })}
        >
          Add Field
        </CustomButton>
      </Section>

      <Section
        title="Response Body"
        description="Fields to read from the API response"
        icon={<ListTree className="h-3.5 w-3.5" />}
      >
        {arr('responseFields').length === 0 ? (
          <Empty>No response fields. The AI uses the raw response.</Empty>
        ) : (
          arr('responseFields').map((f, i) => (
            <div key={i} className="flex items-center gap-2">
              <TextInput
                name={`rf-${i}`}
                value={s(f.name)}
                onChange={(e) => upd('responseFields', i, { name: e.target.value })}
                placeholder="field_name"
                className="flex-1 font-mono"
              />
              <div className="w-28 shrink-0">
                <SelectInput
                  name={`rt-${i}`}
                  options={PROP_TYPES}
                  value={s(f.type) || 'string'}
                  onValueChange={(v) => upd('responseFields', i, { type: v })}
                />
              </div>
              <RemoveBtn onClick={() => del('responseFields', i)} label="Remove field" />
            </div>
          ))
        )}
        <CustomButton
          type="text"
          size="xs"
          icon={<Plus className="h-3.5 w-3.5" />}
          onClick={() => add('responseFields', { name: '', type: 'string', required: false })}
        >
          Add Property
        </CustomButton>
      </Section>

      <Section
        title="Aliases"
        description="Rename response fields for use in later steps"
        icon={<Repeat2 className="h-3.5 w-3.5" />}
      >
        {arr('aliases').length === 0 ? (
          <Empty>No aliases configured.</Empty>
        ) : (
          arr('aliases').map((a, i) => (
            <div key={i} className="flex items-center gap-2">
              <TextInput
                name={`af-${i}`}
                value={s(a.responseField)}
                onChange={(e) => upd('aliases', i, { responseField: e.target.value })}
                placeholder="response.field"
                className="flex-1 font-mono"
              />
              <span className="text-muted-foreground">→</span>
              <TextInput
                name={`aa-${i}`}
                value={s(a.alias)}
                onChange={(e) => upd('aliases', i, { alias: e.target.value })}
                placeholder="alias_name"
                className="flex-1 font-mono"
              />
              <RemoveBtn onClick={() => del('aliases', i)} label="Remove alias" />
            </div>
          ))
        )}
        <CustomButton
          type="text"
          size="xs"
          icon={<Plus className="h-3.5 w-3.5" />}
          onClick={() => add('aliases', { responseField: '', alias: '' })}
        >
          Add Alias
        </CustomButton>
      </Section>

      <Section
        title="Messages"
        description="What the agent says before making the call"
        icon={<Send className="h-3.5 w-3.5" />}
      >
        <TextInput
          name="msg-start"
          label="Before calling (optional)"
          value={s(messages.start)}
          onChange={(e) => setMsg('start', e.target.value)}
          placeholder="One moment while I look that up…"
        />
      </Section>
    </div>
  );
};

export default ApiRequestForm;
