import Heading from '@tiptap/extension-heading'
import Link from '@tiptap/extension-link'
import Paragraph from '@tiptap/extension-paragraph'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { useEffect, useState } from 'react'

import {
    Box,
    Divider,
    FormControl,
    IconButton,
    MenuItem,
    Paper,
    Select,
    Stack,
    Typography,
} from '@mui/material'

import {
    AlignCenter,
    AlignLeft,
    AlignRight,
    Bold,
    Italic,
    List,
    Underline as Under,
} from 'lucide-react'

type StepThreeProps = {
  formData: {
    voicePrompting?: string
  }
  onFormChange: <T extends object>(partial: T) => void
}

export default function StepThree({ formData, onFormChange }: StepThreeProps) {
  const [headingType, setHeadingType] = useState<'normal' | 'heading1' | 'heading2' | 'heading3'>('normal')

  const [active, setActive] = useState({
    bold: false,
    italic: false,
    underline: false,
    bulletList: false,
    align: 'left' as 'left' | 'center' | 'right',
  })

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

    // ✅ Load initial value from parent
    content: formData.voicePrompting || '',

    // ✅ STORE VALUE IN PARENT
    onUpdate({ editor }) {
      const html = editor.getHTML()
      onFormChange({ voicePrompting: html })
    },
  })

  /* 🔁 Sync toolbar state */
  useEffect(() => {
    if (!editor) return

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
      })

      if (editor.isActive('heading', { level: 1 })) setHeadingType('heading1')
      else if (editor.isActive('heading', { level: 2 })) setHeadingType('heading2')
      else if (editor.isActive('heading', { level: 3 })) setHeadingType('heading3')
      else setHeadingType('normal')
    }

    editor.on('selectionUpdate', syncState)
    editor.on('transaction', syncState)

    return () => {
      editor.off('selectionUpdate', syncState)
      editor.off('transaction', syncState)
    }
  }, [editor])

  const toggleStyle = (style: string) => {
    if (!editor) return
    const chain = editor.chain().focus()

    switch (style) {
      case 'bold':
        chain.toggleBold().run()
        break
      case 'italic':
        chain.toggleItalic().run()
        break
      case 'underline':
        chain.toggleUnderline().run()
        break
      case 'bulletList':
        chain.toggleBulletList().run()
        break
      case 'left':
        chain.setTextAlign('left').run()
        break
      case 'center':
        chain.setTextAlign('center').run()
        break
      case 'right':
        chain.setTextAlign('right').run()
        break
    }
  }

  const handleHeadingChange = (e: any) => {
    if (!editor) return
    const value = e.target.value
    setHeadingType(value)

    const chain = editor.chain().focus()

    if (value === 'normal') chain.setParagraph().run()
    if (value === 'heading1') chain.toggleHeading({ level: 1 }).run()
    if (value === 'heading2') chain.toggleHeading({ level: 2 }).run()
    if (value === 'heading3') chain.toggleHeading({ level: 3 }).run()
  }

  const clearContent = () => {
    editor?.commands.clearContent()
    editor?.commands.focus()
    onFormChange({ voicePrompting: '' })
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography fontSize={14} color="text.secondary" mb={2}>
        Below is an AI-generated job description. You can edit it or clear it.
      </Typography>

      <Paper variant="outlined" sx={{ borderRadius: 1, overflow: 'hidden' }}>
        {/* Toolbar */}
        <Stack direction="row" alignItems="center" spacing={1} px={2} py={1}>
          <FormControl size="small">
            <Select value={headingType} onChange={handleHeadingChange} sx={{ minWidth: 130 }}>
              <MenuItem value="normal">Normal</MenuItem>
              <MenuItem value="heading1">Heading 1</MenuItem>
              <MenuItem value="heading2">Heading 2</MenuItem>
              <MenuItem value="heading3">Heading 3</MenuItem>
            </Select>
          </FormControl>

          <Divider orientation="vertical" flexItem />

          <IconButton color={active.bold ? 'primary' : 'default'} onClick={() => toggleStyle('bold')}>
            <Bold size={18} />
          </IconButton>

          <IconButton color={active.italic ? 'primary' : 'default'} onClick={() => toggleStyle('italic')}>
            <Italic size={18} />
          </IconButton>

          <IconButton color={active.underline ? 'primary' : 'default'} onClick={() => toggleStyle('underline')}>
            <Under size={18} />
          </IconButton>

          <Divider orientation="vertical" flexItem />

          <IconButton color={active.bulletList ? 'primary' : 'default'} onClick={() => toggleStyle('bulletList')}>
            <List size={18} />
          </IconButton>

          <Divider orientation="vertical" flexItem />

          <IconButton color={active.align === 'left' ? 'primary' : 'default'} onClick={() => toggleStyle('left')}>
            <AlignLeft size={18} />
          </IconButton>

          <IconButton color={active.align === 'center' ? 'primary' : 'default'} onClick={() => toggleStyle('center')}>
            <AlignCenter size={18} />
          </IconButton>

          <IconButton color={active.align === 'right' ? 'primary' : 'default'} onClick={() => toggleStyle('right')}>
            <AlignRight size={18} />
          </IconButton>

          <Box flexGrow={1} />

          <Typography fontSize={14} color="error.main" sx={{ cursor: 'pointer' }} onClick={clearContent}>
            Clear all
          </Typography>
        </Stack>

        <Divider />

        {/* Editor */}
        <Box
          px={2}
          py={2}
          minHeight={460}
          onClick={() => editor?.commands.focus()}
          sx={{
            cursor: 'text',
            '& .ProseMirror': {
              outline: 'none',
              minHeight: 180,
              fontSize: 14,
              lineHeight: 1.6,
            },
          }}
        >
          <EditorContent editor={editor} />
        </Box>
      </Paper>
    </Box>
  )
}
