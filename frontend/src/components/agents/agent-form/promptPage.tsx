'use client';

import { CustomButton, SelectInput } from '@/components/shared';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/utils/cn';
import Heading from '@tiptap/extension-heading';
import Link from '@tiptap/extension-link';
import Paragraph from '@tiptap/extension-paragraph';
import TextAlign from '@tiptap/extension-text-align';
import Underline from '@tiptap/extension-underline';
import { EditorContent, useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import {
  AlignCenter,
  AlignLeft,
  AlignRight,
  Bold,
  Italic,
  List,
  Trash2,
  Underline as Under,
} from 'lucide-react';
import type { MouseEvent, ReactNode } from 'react';
import { useEffect, useState } from 'react';

interface PromptPageProps {
  formData: {
    voicePrompting?: string;
  };
  onFormChange: <T extends object>(partial: T) => void;
}

const HEADING_OPTIONS = [
  { value: 'normal', label: 'Normal' },
  { value: 'heading1', label: 'Heading 1' },
  { value: 'heading2', label: 'Heading 2' },
  { value: 'heading3', label: 'Heading 3' },
];

function ToolbarButton({
  isActive,
  onClick,
  children,
}: {
  isActive: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <CustomButton
      type="text"
      htmlType="button"
      size="icon-sm"
      className={cn('rounded-md transition-colors', isActive && 'bg-accent text-accent-foreground')}
      onMouseDown={(e: MouseEvent) => e.preventDefault()}
      onClick={onClick}
    >
      {children}
    </CustomButton>
  );
}

function ToolbarDivider() {
  return <Separator orientation="vertical" className="mx-1.5 !h-5" />;
}

export default function PromptPage({ formData, onFormChange }: PromptPageProps) {
  const [headingType, setHeadingType] = useState<'normal' | 'heading1' | 'heading2' | 'heading3'>(
    'normal',
  );

  const [active, setActive] = useState({
    bold: false,
    italic: false,
    underline: false,
    bulletList: false,
    align: 'left' as 'left' | 'center' | 'right',
  });

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit.configure({
        heading: false,
        paragraph: false,
      }),
      Paragraph,
      Heading.configure({ levels: [1, 2, 3] }),
      Underline,
      Link.configure({ openOnClick: false }),
      TextAlign.configure({
        types: ['heading', 'paragraph'],
      }),
    ],
    editorProps: {
      attributes: {
        class: 'ProseMirror',
      },
    },
    content: formData.voicePrompting || '',
    onUpdate({ editor }) {
      onFormChange({ voicePrompting: editor.getHTML() });
    },
  });

  useEffect(() => {
    if (!editor) return;

    const syncState = () => {
      setActive({
        bold: editor.isActive('bold'),
        italic: editor.isActive('italic'),
        underline: editor.isActive('underline'),
        bulletList: editor.isActive('bulletList'),
        align: editor.isActive({ textAlign: 'center' })
          ? 'center'
          : editor.isActive({ textAlign: 'right' })
            ? 'right'
            : 'left',
      });

      if (editor.isActive('heading', { level: 1 })) setHeadingType('heading1');
      else if (editor.isActive('heading', { level: 2 })) setHeadingType('heading2');
      else if (editor.isActive('heading', { level: 3 })) setHeadingType('heading3');
      else setHeadingType('normal');
    };

    editor.on('selectionUpdate', syncState);
    editor.on('transaction', syncState);

    return () => {
      editor.off('selectionUpdate', syncState);
      editor.off('transaction', syncState);
    };
  }, [editor]);

  const toggleStyle = (style: string) => {
    if (!editor) return;
    const chain = editor.chain().focus();

    switch (style) {
      case 'bold':
        chain.toggleBold().run();
        break;
      case 'italic':
        chain.toggleItalic().run();
        break;
      case 'underline':
        chain.toggleUnderline().run();
        break;
      case 'bulletList':
        chain.toggleBulletList().run();
        break;
      case 'left':
        chain.setTextAlign('left').run();
        break;
      case 'center':
        chain.setTextAlign('center').run();
        break;
      case 'right':
        chain.setTextAlign('right').run();
        break;
    }
  };

  const handleHeadingChange = (value: string) => {
    if (!editor) return;
    setHeadingType(value as typeof headingType);

    const chain = editor.chain().focus();

    if (value === 'normal') chain.setParagraph().run();
    if (value === 'heading1') chain.toggleHeading({ level: 1 }).run();
    if (value === 'heading2') chain.toggleHeading({ level: 2 }).run();
    if (value === 'heading3') chain.toggleHeading({ level: 3 }).run();
  };

  const clearContent = () => {
    editor?.commands.clearContent();
    editor?.commands.focus();
    onFormChange({ voicePrompting: '' });
  };

  return (
    <div className="space-y-3">
      <p className="text-[13px] leading-relaxed text-muted-foreground">
        Below is an AI-generated job description. You can edit it or clear it.
      </p>

      <div className="overflow-hidden rounded-lg border border-border bg-background">
        {/* Toolbar */}
        <div className="flex items-center gap-1 border-b border-border bg-muted/30 px-3 py-1.5">
          <SelectInput
            name="headingType"
            value={headingType}
            onValueChange={handleHeadingChange}
            options={HEADING_OPTIONS}
            size="sm"
            className="w-[130px]"
          />

          <ToolbarDivider />

          <ToolbarButton isActive={active.bold} onClick={() => toggleStyle('bold')}>
            <Bold size={16} />
          </ToolbarButton>

          <ToolbarButton isActive={active.italic} onClick={() => toggleStyle('italic')}>
            <Italic size={16} />
          </ToolbarButton>

          <ToolbarButton isActive={active.underline} onClick={() => toggleStyle('underline')}>
            <Under size={16} />
          </ToolbarButton>

          <ToolbarDivider />

          <ToolbarButton isActive={active.bulletList} onClick={() => toggleStyle('bulletList')}>
            <List size={16} />
          </ToolbarButton>

          <ToolbarDivider />

          <ToolbarButton isActive={active.align === 'left'} onClick={() => toggleStyle('left')}>
            <AlignLeft size={16} />
          </ToolbarButton>

          <ToolbarButton isActive={active.align === 'center'} onClick={() => toggleStyle('center')}>
            <AlignCenter size={16} />
          </ToolbarButton>

          <ToolbarButton isActive={active.align === 'right'} onClick={() => toggleStyle('right')}>
            <AlignRight size={16} />
          </ToolbarButton>

          <div className="flex-1" />

          <CustomButton
            type="text"
            className="gap-1.5 text-[13px] text-destructive hover:text-destructive/80"
            onClick={clearContent}
            icon={<Trash2 size={14} />}
          >
            Clear all
          </CustomButton>
        </div>

        {/* Editor */}
        <div
          className="min-h-[380px] cursor-text px-4 py-4 [&_.ProseMirror]:min-h-[180px] [&_.ProseMirror]:text-sm [&_.ProseMirror]:leading-relaxed [&_.ProseMirror]:outline-none"
          onClick={() => editor?.commands.focus()}
        >
          <EditorContent editor={editor} />
        </div>
      </div>
    </div>
  );
}
