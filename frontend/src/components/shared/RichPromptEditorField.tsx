'use client';

import { EditorContent, useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Settings2, Sparkles, Variable } from 'lucide-react';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Controller } from 'react-hook-form';

import CustomButton from '@/components/shared/CustomButton';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { PROMPT_VARIABLES, type PromptVariable } from '@/constants/promptVariables';
import type {
  FormRichPromptEditorFieldProps,
  RichPromptEditorFieldBaseProps,
} from '@/types/components';
import { cn } from '@/utils/cn';

import ManageVariablesModal from './rich-prompt-editor/ManageVariablesModal';
import {
  parseTextToDoc,
  serializeToText,
  VARIABLE_MENTION_NAME,
} from './rich-prompt-editor/serialization';
import VariableMention from './rich-prompt-editor/variableMention';

type RichPromptEditorFieldProps = RichPromptEditorFieldBaseProps | FormRichPromptEditorFieldProps;

function isFormField(props: RichPromptEditorFieldProps): props is FormRichPromptEditorFieldProps {
  return 'control' in props && props.control !== undefined;
}

// Plain prompt text only — disable every formatting node/mark StarterKit ships so the
// document stays paragraphs + variable chips (no headings, lists, bold, links, …).
const STARTER_KIT = StarterKit.configure({
  heading: false,
  bold: false,
  italic: false,
  strike: false,
  code: false,
  codeBlock: false,
  blockquote: false,
  bulletList: false,
  orderedList: false,
  listItem: false,
  listKeymap: false,
  horizontalRule: false,
  link: false,
  underline: false,
});

const EXTENSIONS = [STARTER_KIT, VariableMention];

const Skeleton = ({ className }: { className?: string }) => (
  <div className={cn('animate-pulse rounded-lg bg-muted', className)} />
);

function PlainRichPromptEditorField({
  name,
  label,
  value = '',
  onChange,
  placeholder,
  isRequired = false,
  loading = false,
  disabled = false,
  error = false,
  helperText,
  className,
  labelClassName,
  id,
  minHeight = '220px',
  maxHeight,
  fill = false,
}: RichPromptEditorFieldBaseProps) {
  // Latest onChange in a ref so the editor instance is created once (a changing
  // onChange identity must not re-create the editor / lose the caret).
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  const [isEmpty, setIsEmpty] = useState(!value);

  // Parse the initial value exactly once; later external changes flow through the
  // sync effect below. (Computed lazily so it doesn't re-parse on every render.)
  const initialContentRef = useRef<ReturnType<typeof parseTextToDoc> | null>(null);
  if (initialContentRef.current === null) initialContentRef.current = parseTextToDoc(value);

  const editor = useEditor({
    immediatelyRender: false,
    editable: !disabled,
    extensions: EXTENSIONS,
    content: initialContentRef.current, // initial only; synced via effect
    editorProps: {
      attributes: {
        class: 'outline-none whitespace-pre-wrap break-words leading-relaxed',
        // In fill mode the ProseMirror element fills the (flex) surface; otherwise it
        // uses the fixed min height and the page/parent grows with content.
        style: `min-height:${fill ? '100%' : minHeight}`,
        ...(id ? { id } : {}),
      },
    },
    onUpdate: ({ editor }) => {
      const text = serializeToText(editor.getJSON());
      setIsEmpty(editor.isEmpty);
      onChangeRef.current?.(text);
    },
  });

  // Keep the editor in sync with external value changes (e.g. async load in edit mode).
  // emitUpdate:false avoids re-firing onChange (and an RHF feedback loop); the guard
  // avoids resetting the caret on the value updates we ourselves emitted.
  useEffect(() => {
    if (!editor) return;
    const current = serializeToText(editor.getJSON());
    if (value !== current) {
      editor.commands.setContent(parseTextToDoc(value), { emitUpdate: false });
      setIsEmpty(editor.isEmpty);
    }
  }, [value, editor]);

  // Pass emitUpdate=false: setEditable defaults to firing an "update" event,
  // which would call onUpdate → field.onChange on mount and mark the RHF form
  // dirty (ProseMirror's schema normalisation makes the round-tripped text
  // differ subtly from the loaded value, so RHF's deep-equality flips isDirty).
  useEffect(() => {
    editor?.setEditable(!disabled, false);
  }, [disabled, editor]);

  const [pickerOpen, setPickerOpen] = useState(false);
  const [manageOpen, setManageOpen] = useState(false);
  const insertVariable = useCallback(
    (variable: PromptVariable) => {
      if (!editor) return;
      editor
        .chain()
        .focus()
        .insertContent([
          { type: VARIABLE_MENTION_NAME, attrs: { key: variable.key } },
          { type: 'text', text: ' ' },
        ])
        .run();
      setPickerOpen(false);
    },
    [editor],
  );

  if (loading) {
    return (
      <div>
        {label && <Skeleton className="mb-1.5 h-4 w-24" />}
        <Skeleton className="h-[220px] w-full" />
      </div>
    );
  }

  return (
    <div className={cn(fill && 'flex min-h-0 flex-1 flex-col')}>
      {label && (
        <Label htmlFor={id ?? name} className={cn('mb-1.5 block shrink-0', labelClassName)}>
          {label}
          {isRequired && <span className="ml-0.5 text-destructive">*</span>}
        </Label>
      )}

      <div
        className={cn(
          'overflow-hidden rounded-lg border border-input bg-transparent shadow-xs transition-[color,box-shadow]',
          'focus-within:border-ring focus-within:ring-[3px] focus-within:ring-ring/50',
          error &&
            'border-destructive focus-within:border-destructive focus-within:ring-destructive/50',
          disabled && 'pointer-events-none opacity-60',
          fill && 'flex min-h-0 flex-1 flex-col',
          className,
        )}
      >
        {/* Toolbar */}
        <div className="flex shrink-0 items-center justify-between gap-2 border-b border-border/60 bg-muted/30 px-2 py-1.5">
          <span className="inline-flex select-none items-center gap-1.5 pl-1 text-[11px] font-medium text-muted-foreground">
            <Sparkles className="size-3" />
            Variables
          </span>
          <div className="flex items-center gap-1.5">
            <Popover open={pickerOpen} onOpenChange={setPickerOpen}>
              <PopoverTrigger asChild>
                <CustomButton
                  type="default"
                  size="sm"
                  disabled={disabled}
                  icon={<Variable className="size-3.5" />}
                >
                  Insert variable
                </CustomButton>
              </PopoverTrigger>
              <PopoverContent align="end" className="w-72 p-1">
                <div className="border-b border-border/60 px-2 pb-1.5 pt-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  System variables
                </div>
                <div className="mt-1 max-h-64 overflow-auto">
                  {PROMPT_VARIABLES.map((variable) => (
                    <button
                      key={variable.key}
                      type="button"
                      onClick={() => insertVariable(variable)}
                      className="flex w-full flex-col items-start gap-0.5 rounded-md px-2 py-1.5 text-left hover:bg-accent"
                    >
                      <span className="flex items-baseline gap-1.5 text-sm font-medium">
                        {variable.label}
                        <span className="font-mono text-[11px] text-muted-foreground">{`{{${variable.key}}}`}</span>
                      </span>
                      <span className="text-xs text-muted-foreground">{variable.description}</span>
                    </button>
                  ))}
                </div>
              </PopoverContent>
            </Popover>
            <CustomButton
              type="default"
              size="sm"
              disabled={disabled}
              onClick={() => setManageOpen(true)}
              icon={<Settings2 className="size-3.5" />}
            >
              Custom variables
            </CustomButton>
          </div>
        </div>

        {/* Editor surface — scrolls internally in fill mode or when maxHeight is set */}
        <div
          className={cn(
            'relative px-3 py-2.5 text-sm',
            fill ? 'min-h-0 flex-1 overflow-y-auto' : maxHeight && 'overflow-y-auto',
          )}
          style={!fill && maxHeight ? { maxHeight } : undefined}
        >
          {isEmpty && placeholder && (
            <div className="pointer-events-none absolute left-3 top-2.5 whitespace-pre-wrap leading-relaxed text-muted-foreground">
              {placeholder}
            </div>
          )}
          <EditorContent editor={editor} />
        </div>
      </div>

      {helperText && (
        <p
          className={cn(
            'mt-1 shrink-0 text-xs',
            error ? 'text-destructive' : 'text-muted-foreground',
          )}
        >
          {helperText}
        </p>
      )}

      <ManageVariablesModal
        editor={editor}
        open={manageOpen}
        onClose={() => setManageOpen(false)}
      />
    </div>
  );
}

const MemoizedPlain = React.memo(PlainRichPromptEditorField);

function RichPromptEditorField(props: RichPromptEditorFieldProps) {
  if (isFormField(props)) {
    const { name, control, rules, onValueChange, error, helperText, ...rest } = props;
    return (
      <Controller
        name={name}
        control={control}
        rules={rules}
        render={({ field, fieldState }) => (
          <MemoizedPlain
            {...rest}
            name={name}
            value={field.value ?? ''}
            onChange={(val) => {
              field.onChange(val);
              onValueChange?.(val);
            }}
            error={error ?? !!fieldState.error}
            helperText={helperText ?? (fieldState.error?.message as string)}
          />
        )}
      />
    );
  }

  return <MemoizedPlain {...props} />;
}

export default React.memo(RichPromptEditorField);
