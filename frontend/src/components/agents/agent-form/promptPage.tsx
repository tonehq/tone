'use client';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
  Underline as Under,
} from 'lucide-react';
import { useEffect, useState } from 'react';

interface StepThreeProps {
  formData: {
    voicePrompting?: string;
  };
  onFormChange: <T extends object>(partial: T) => void;
}

export default function StepThree({ formData, onFormChange }: StepThreeProps) {
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
      const html = editor.getHTML();
      onFormChange({ voicePrompting: html });
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
    <div className="p-6">
      <p className="mb-3 text-[13px] leading-relaxed text-muted-foreground">
        Below is an AI-generated job description. You can edit it or clear it.
      </p>

      <Card className="gap-0 overflow-hidden rounded-lg border py-0 shadow-none">
        {/* Toolbar */}
        <div className="flex items-center gap-1 px-2 py-1">
          <Select value={headingType} onValueChange={handleHeadingChange}>
            <SelectTrigger size="sm" className="min-w-[130px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="normal">Normal</SelectItem>
              <SelectItem value="heading1">Heading 1</SelectItem>
              <SelectItem value="heading2">Heading 2</SelectItem>
              <SelectItem value="heading3">Heading 3</SelectItem>
            </SelectContent>
          </Select>

          <Separator orientation="vertical" className="mx-1 h-6" />

          <Button
            variant="ghost"
            size="icon-sm"
            className={cn(active.bold && 'bg-accent')}
            onClick={() => toggleStyle('bold')}
          >
            <Bold size={18} />
          </Button>

          <Button
            variant="ghost"
            size="icon-sm"
            className={cn(active.italic && 'bg-accent')}
            onClick={() => toggleStyle('italic')}
          >
            <Italic size={18} />
          </Button>

          <Button
            variant="ghost"
            size="icon-sm"
            className={cn(active.underline && 'bg-accent')}
            onClick={() => toggleStyle('underline')}
          >
            <Under size={18} />
          </Button>

          <Separator orientation="vertical" className="mx-1 h-6" />

          <Button
            variant="ghost"
            size="icon-sm"
            className={cn(active.bulletList && 'bg-accent')}
            onClick={() => toggleStyle('bulletList')}
          >
            <List size={18} />
          </Button>

          <Separator orientation="vertical" className="mx-1 h-6" />

          <Button
            variant="ghost"
            size="icon-sm"
            className={cn(active.align === 'left' && 'bg-accent')}
            onClick={() => toggleStyle('left')}
          >
            <AlignLeft size={18} />
          </Button>

          <Button
            variant="ghost"
            size="icon-sm"
            className={cn(active.align === 'center' && 'bg-accent')}
            onClick={() => toggleStyle('center')}
          >
            <AlignCenter size={18} />
          </Button>

          <Button
            variant="ghost"
            size="icon-sm"
            className={cn(active.align === 'right' && 'bg-accent')}
            onClick={() => toggleStyle('right')}
          >
            <AlignRight size={18} />
          </Button>

          <div className="flex-1" />

          <button
            type="button"
            className="text-sm text-destructive hover:text-destructive/80"
            onClick={clearContent}
          >
            Clear all
          </button>
        </div>

        <Separator />

        {/* Editor */}
        <div
          className="min-h-[460px] cursor-text px-4 py-4 [&_.ProseMirror]:min-h-[180px] [&_.ProseMirror]:text-sm [&_.ProseMirror]:leading-relaxed [&_.ProseMirror]:outline-none"
          onClick={() => editor?.commands.focus()}
        >
          <EditorContent editor={editor} />
        </div>
      </Card>
    </div>
  );
}
