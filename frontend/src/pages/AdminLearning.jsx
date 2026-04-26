import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  GraduationCap, Plus, Trash2, ChevronDown, ChevronRight, ChevronsLeft, ChevronsRight,
  FolderPlus, FilePlus, Save, Eye, EyeOff, Image as ImageIcon, Globe, Sparkles, FileDown, Maximize2, Minimize2, Pencil, X,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '../AuthContext';
import { useConfirm } from '../components/Confirm';
import {
  adminLearnListSections, adminLearnCreateSection, adminLearnUpdateSection, adminLearnDeleteSection,
  adminLearnListLessons, adminLearnCreateLesson, adminLearnUpdateLesson, adminLearnDeleteLesson,
  adminLearnUploadAsset, adminLearnExportLatex,
} from '../api';
import LessonMarkdown from '../components/learning/LessonMarkdown';
import MarkdownEditor from '../components/learning/MarkdownEditor';
import WidgetCatalog from '../components/learning/WidgetCatalog';
import ExercisePickerModal from '../components/learning/ExercisePickerModal';

// Slug helper — keeps the admin from having to type a URL-safe id.
function slugify(s) {
  return (s || '')
    .toLowerCase()
    .trim()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)+/g, '')
    .slice(0, 80) || 'untitled';
}

export default function AdminLearning() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const confirm = useConfirm();

  const [sections, setSections] = useState([]);
  const [expandedSectionId, setExpandedSectionId] = useState(null);
  const [lessonsBySection, setLessonsBySection] = useState({});
  const [editingLesson, setEditingLesson] = useState(null); // { ...lessonData, _sectionId }
  const [editLang, setEditLang] = useState('fr');
  const [showCatalog, setShowCatalog] = useState(false);
  const [showExercisePicker, setShowExercisePicker] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [showPreview, setShowPreview] = useState(true);
  const [editingSection, setEditingSection] = useState(null);  // { id, title_fr, ... }
  const [treeCollapsed, setTreeCollapsed] = useState(false);

  useEffect(() => {
    if (!user?.is_admin) navigate('/dashboard');
  }, [user, navigate]);

  const reloadSections = async () => {
    try {
      const r = await adminLearnListSections();
      setSections(r.data || []);
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.learning.toastFailed'));
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await adminLearnListSections();
        if (!cancelled) setSections(r.data || []);
      } catch (err) {
        if (!cancelled) toast.error(err.response?.data?.detail || t('admin.learning.toastFailed'));
      }
    })();
    return () => { cancelled = true; };
  }, [t]);

  const reloadLessons = async (sectionId) => {
    try {
      const r = await adminLearnListLessons(sectionId);
      setLessonsBySection((prev) => ({ ...prev, [sectionId]: r.data || [] }));
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.learning.toastFailed'));
    }
  };

  const toggleSection = async (s) => {
    if (expandedSectionId === s.id) {
      setExpandedSectionId(null);
      return;
    }
    setExpandedSectionId(s.id);
    if (!lessonsBySection[s.id]) {
      await reloadLessons(s.id);
    }
  };

  const handleAddSection = async () => {
    const title = window.prompt(t('admin.learning.promptSectionTitle'));
    if (!title) return;
    try {
      await adminLearnCreateSection({
        slug: slugify(title),
        title_fr: title, title_en: title,
        description_fr: '', description_en: '',
        order_idx: sections.length,
        is_published: false,
      });
      toast.success(t('admin.learning.toastCreated'));
      reloadSections();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.learning.toastFailed'));
    }
  };

  const handleDeleteSection = async (s) => {
    const ok = await confirm({
      message: t('admin.learning.confirmDeleteSection', { title: s.title_fr }),
      danger: true,
    });
    if (!ok) return;
    try {
      await adminLearnDeleteSection(s.id);
      toast.success(t('admin.learning.toastDeleted'));
      reloadSections();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.learning.toastFailed'));
    }
  };

  const handleToggleSectionPublished = async (s) => {
    try {
      await adminLearnUpdateSection(s.id, { ...s, is_published: !s.is_published });
      reloadSections();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.learning.toastFailed'));
    }
  };

  const handleAddLesson = async (sectionId) => {
    const title = window.prompt(t('admin.learning.promptLessonTitle'));
    if (!title) return;
    try {
      const r = await adminLearnCreateLesson(sectionId, {
        slug: slugify(title),
        title_fr: title, title_en: title,
        content_fr: '', content_en: '',
        order_idx: (lessonsBySection[sectionId] || []).length,
        is_published: false,
      });
      toast.success(t('admin.learning.toastCreated'));
      reloadLessons(sectionId);
      setEditingLesson({ ...r.data, _sectionId: sectionId });
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.learning.toastFailed'));
    }
  };

  const handleEditLesson = async (lesson, sectionId) => {
    // Need the full body; the listing only has the summary.
    try {
      const { learnGetLesson } = await import('../api');
      const r = await learnGetLesson(lesson.id);
      setEditingLesson({ ...r.data, _sectionId: sectionId });
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.learning.toastFailed'));
    }
  };

  const handleSaveLesson = async () => {
    if (!editingLesson) return;
    const { id, _sectionId, ...rest } = editingLesson;
    try {
      const r = await adminLearnUpdateLesson(id, {
        slug: rest.slug,
        title_fr: rest.title_fr, title_en: rest.title_en,
        content_fr: rest.content_fr, content_en: rest.content_en,
        order_idx: rest.order_idx,
        is_published: rest.is_published,
        exercise_problem_id: rest.exercise_problem_id || null,
      });
      toast.success(t('admin.learning.toastSaved'));
      setEditingLesson({ ...r.data, _sectionId });
      reloadLessons(_sectionId);
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.learning.toastFailed'));
    }
  };

  const handleDeleteLesson = async (lesson, sectionId) => {
    const ok = await confirm({
      message: t('admin.learning.confirmDeleteLesson', { title: lesson.title_fr }),
      danger: true,
    });
    if (!ok) return;
    try {
      await adminLearnDeleteLesson(lesson.id);
      toast.success(t('admin.learning.toastDeleted'));
      if (editingLesson?.id === lesson.id) setEditingLesson(null);
      reloadLessons(sectionId);
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.learning.toastFailed'));
    }
  };


  const handleExportLatex = async (lang) => {
    setExporting(true);
    try {
      const r = await adminLearnExportLatex(lang);
      // r.data is a Blob (responseType: 'blob' in api.js).
      const blob = new Blob([r.data], { type: 'application/zip' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      link.download = `codearena-syllabus-${lang}-${today}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast.success(t('admin.learning.toastExportOk'));
    } catch (err) {
      toast.error(err.response?.data?.detail || t('admin.learning.toastFailed'));
    } finally {
      setExporting(false);
    }
  };

  const insertWidget = (snippet) => {
    if (!editingLesson) return;
    setEditingLesson((prev) => ({
      ...prev,
      [`content_${editLang}`]: (prev[`content_${editLang}`] || '') + '\n\n' + snippet + '\n',
    }));
  };

  const editorContent = editingLesson?.[`content_${editLang}`] ?? '';
  const editorTitle = editingLesson?.[`title_${editLang}`] ?? '';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
          <GraduationCap className="w-8 h-8 text-violet-500" />
          {t('admin.learning.title')}
        </h1>
        <div className="flex items-center gap-2">
          <div className="relative group">
            <button
              disabled={exporting}
              className="btn-secondary inline-flex items-center gap-2"
              title={t('admin.learning.exportHint')}
            >
              <FileDown className="w-4 h-4" />
              {exporting ? t('admin.learning.exporting') : t('admin.learning.export')}
            </button>
            {/* Lightweight dropdown — hover/focus reveals language picker. */}
            <div className="absolute right-0 mt-1 hidden group-hover:block group-focus-within:block bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg shadow-lg overflow-hidden z-10 min-w-[160px]">
              <button
                onClick={() => handleExportLatex('fr')}
                className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-slate-700"
              >
                LaTeX · FR
              </button>
              <button
                onClick={() => handleExportLatex('en')}
                className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-slate-700"
              >
                LaTeX · EN
              </button>
            </div>
          </div>
          <button
            onClick={() => navigate('/admin/learning/widgets')}
            className="btn-secondary inline-flex items-center gap-2"
            title={t('admin.learning.manageWidgetsHint')}
          >
            <Sparkles className="w-4 h-4" />
            {t('admin.learning.manageWidgets')}
          </button>
          <button onClick={handleAddSection} className="btn-primary inline-flex items-center gap-2">
            <FolderPlus className="w-4 h-4" />
            {t('admin.learning.newSection')}
          </button>
        </div>
      </div>

      <div className={`grid grid-cols-1 gap-6 ${treeCollapsed ? 'lg:grid-cols-[40px_1fr]' : 'lg:grid-cols-12'}`}>
        {/* Tree of sections + lessons. Collapsed = a thin rail with a
            single chevron-right button to expand. Helps when the
            admin wants the editor to take the full width. */}
        {treeCollapsed ? (
          <div className="hidden lg:flex flex-col items-center pt-2">
            <button
              onClick={() => setTreeCollapsed(false)}
              className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-slate-800 dark:hover:bg-slate-800/50 dark:text-gray-400 dark:hover:text-gray-200"
              title={t('admin.learning.expandTree')}
            >
              <ChevronsRight className="w-4 h-4" />
            </button>
          </div>
        ) : null}
        <div className={`${treeCollapsed ? 'hidden' : 'lg:col-span-4'} space-y-3`}>
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wide font-semibold text-slate-500 dark:text-gray-400">
              {t('admin.learning.tree')}
            </span>
            <button
              onClick={() => setTreeCollapsed(true)}
              className="hidden lg:inline-flex p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 dark:hover:bg-slate-800/50 dark:text-gray-500 dark:hover:text-gray-200"
              title={t('admin.learning.collapseTree')}
            >
              <ChevronsLeft className="w-4 h-4" />
            </button>
          </div>
          {sections.length === 0 && (
            <div className="glass-card p-6 text-center text-sm text-slate-500 dark:text-gray-400">
              {t('admin.learning.emptyHint')}
            </div>
          )}
          {sections.map((s) => (
            <div key={s.id} className="glass-card overflow-hidden">
              <div className="flex items-center px-3 py-2 gap-2">
                <button
                  onClick={() => toggleSection(s)}
                  className="text-slate-400 hover:text-slate-600 dark:text-gray-500 dark:hover:text-gray-300"
                >
                  {expandedSectionId === s.id
                    ? <ChevronDown className="w-4 h-4" />
                    : <ChevronRight className="w-4 h-4" />}
                </button>
                <span className="flex-1 font-medium text-slate-900 dark:text-white truncate">
                  {s.title_fr}
                </span>
                <button
                  onClick={() => handleToggleSectionPublished(s)}
                  className={`text-xs px-2 py-0.5 rounded ${s.is_published
                    ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                    : 'bg-slate-200 text-slate-500 dark:bg-slate-700 dark:text-gray-400'}`}
                  title={t('admin.learning.togglePublish')}
                >
                  {s.is_published ? t('admin.learning.published') : t('admin.learning.draft')}
                </button>
                <button
                  onClick={() => setEditingSection({ ...s })}
                  className="p-1.5 rounded hover:bg-violet-500/10 text-slate-400 hover:text-violet-600 dark:text-gray-500 dark:hover:text-violet-400"
                  title={t('admin.learning.editSection')}
                >
                  <Pencil className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDeleteSection(s)}
                  className="p-1.5 rounded hover:bg-red-500/10 text-slate-400 hover:text-red-500 dark:text-gray-500 dark:hover:text-red-400"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              {editingSection?.id === s.id && (
                <div className="border-t border-gray-100 dark:border-slate-700/50 px-3 py-3 space-y-2 bg-violet-50/30 dark:bg-violet-500/5">
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      className="input-field text-sm"
                      placeholder={t('admin.learning.titleFr')}
                      value={editingSection.title_fr || ''}
                      onChange={(e) => setEditingSection((p) => ({ ...p, title_fr: e.target.value }))}
                    />
                    <input
                      className="input-field text-sm"
                      placeholder={t('admin.learning.titleEn')}
                      value={editingSection.title_en || ''}
                      onChange={(e) => setEditingSection((p) => ({ ...p, title_en: e.target.value }))}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <textarea
                      className="input-field text-sm h-16"
                      placeholder={t('admin.learning.descFr')}
                      value={editingSection.description_fr || ''}
                      onChange={(e) => setEditingSection((p) => ({ ...p, description_fr: e.target.value }))}
                    />
                    <textarea
                      className="input-field text-sm h-16"
                      placeholder={t('admin.learning.descEn')}
                      value={editingSection.description_en || ''}
                      onChange={(e) => setEditingSection((p) => ({ ...p, description_en: e.target.value }))}
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      className="input-field text-xs flex-1"
                      placeholder="slug"
                      value={editingSection.slug || ''}
                      onChange={(e) => setEditingSection((p) => ({ ...p, slug: e.target.value }))}
                    />
                    <button
                      onClick={async () => {
                        try {
                          await adminLearnUpdateSection(editingSection.id, {
                            slug: editingSection.slug,
                            title_fr: editingSection.title_fr,
                            title_en: editingSection.title_en,
                            description_fr: editingSection.description_fr || '',
                            description_en: editingSection.description_en || '',
                            order_idx: editingSection.order_idx ?? 0,
                            is_published: !!editingSection.is_published,
                          });
                          toast.success(t('admin.learning.toastSaved'));
                          setEditingSection(null);
                          reloadSections();
                        } catch (err) {
                          toast.error(err.response?.data?.detail || t('admin.learning.toastFailed'));
                        }
                      }}
                      className="btn-primary text-xs inline-flex items-center gap-1"
                    >
                      <Save className="w-3.5 h-3.5" />
                      {t('admin.learning.save')}
                    </button>
                    <button
                      onClick={() => setEditingSection(null)}
                      className="text-xs px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-gray-200 inline-flex items-center gap-1"
                    >
                      <X className="w-3.5 h-3.5" />
                      {t('admin.learning.cancel')}
                    </button>
                  </div>
                </div>
              )}
              {expandedSectionId === s.id && (
                <div className="border-t border-gray-100 dark:border-slate-700/50 px-3 py-2 space-y-1">
                  {(lessonsBySection[s.id] || []).map((l) => (
                    <div
                      key={l.id}
                      className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer ${
                        editingLesson?.id === l.id
                          ? 'bg-violet-500/10 dark:bg-violet-500/20'
                          : 'hover:bg-slate-100 dark:hover:bg-slate-800/40'
                      }`}
                      onClick={() => handleEditLesson(l, s.id)}
                    >
                      <span className="text-sm flex-1 truncate text-slate-800 dark:text-gray-200">
                        {l.title_fr}
                      </span>
                      {!l.is_published && (
                        <span className="text-[10px] uppercase text-slate-400 dark:text-gray-500">
                          {t('admin.learning.draft')}
                        </span>
                      )}
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDeleteLesson(l, s.id); }}
                        className="p-1 rounded hover:bg-red-500/10 text-slate-400 hover:text-red-500"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={() => handleAddLesson(s.id)}
                    className="w-full text-sm flex items-center justify-center gap-1 py-1.5 text-violet-600 hover:bg-violet-500/10 rounded dark:text-violet-400"
                  >
                    <FilePlus className="w-3.5 h-3.5" />
                    {t('admin.learning.newLesson')}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Editor + preview */}
        <div className={treeCollapsed ? '' : 'lg:col-span-8'}>
          {!editingLesson ? (
            <div className="glass-card p-12 text-center">
              <p className="text-slate-500 dark:text-gray-400">{t('admin.learning.selectLesson')}</p>
            </div>
          ) : (
            <div className="glass-card p-4 space-y-3">
              {/* Lesson metadata row */}
              <div className="flex items-center gap-2 flex-wrap">
                <input
                  className="input-field flex-1 min-w-0"
                  placeholder={t('admin.learning.lessonTitle')}
                  value={editorTitle}
                  onChange={(e) => setEditingLesson((p) => ({ ...p, [`title_${editLang}`]: e.target.value }))}
                />
                <select
                  value={editLang}
                  onChange={(e) => setEditLang(e.target.value)}
                  className="input-field w-24"
                  title={t('admin.learning.editLanguage')}
                >
                  <option value="fr">FR</option>
                  <option value="en">EN</option>
                </select>
                <button
                  onClick={() => setEditingLesson((p) => ({ ...p, is_published: !p.is_published }))}
                  className={`text-sm px-3 py-1.5 rounded-lg ${editingLesson.is_published
                    ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                    : 'bg-slate-200 text-slate-500 dark:bg-slate-700 dark:text-gray-400'}`}
                >
                  {editingLesson.is_published ? t('admin.learning.published') : t('admin.learning.draft')}
                </button>
                <button onClick={handleSaveLesson} className="btn-primary inline-flex items-center gap-2">
                  <Save className="w-4 h-4" />
                  {t('admin.learning.save')}
                </button>
              </div>

              <div className="flex items-center gap-2 text-xs text-slate-400 dark:text-gray-600">
                <span>{t('admin.learning.langCurrent', { lang: editLang.toUpperCase() })}</span>
                <button
                  onClick={() => setShowExercisePicker(true)}
                  className="ml-auto px-2 py-1 rounded bg-amber-100 hover:bg-amber-200 text-amber-700 inline-flex items-center gap-1 dark:bg-amber-500/20 dark:text-amber-300"
                  title={t('admin.learning.manageExercisesHint')}
                >
                  {t('admin.learning.manageExercises')}
                </button>
              </div>

              <WidgetCatalog
                open={showCatalog}
                onClose={() => setShowCatalog(false)}
                onInsert={insertWidget}
              />

              <ExercisePickerModal
                open={showExercisePicker}
                onClose={() => setShowExercisePicker(false)}
                lessonId={editingLesson.id}
                onInsertDirective={(directive) => insertWidget(directive)}
              />

              {/* Toggle for the preview pane — hide it when you want
                  the editor to take the full page width. */}
              <div className="flex items-center justify-end">
                <button
                  onClick={() => setShowPreview((s) => !s)}
                  className="text-xs px-2 py-1 rounded inline-flex items-center gap-1 bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-gray-200"
                  title={showPreview ? t('admin.learning.hidePreview') : t('admin.learning.showPreview')}
                >
                  {showPreview
                    ? <><Minimize2 className="w-3.5 h-3.5" />{t('admin.learning.hidePreview')}</>
                    : <><Maximize2 className="w-3.5 h-3.5" />{t('admin.learning.showPreview')}</>}
                </button>
              </div>

              <div className={`grid gap-3 ${showPreview ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1'}`}>
                <MarkdownEditor
                  value={editorContent}
                  onChange={(v) => setEditingLesson((p) => ({ ...p, [`content_${editLang}`]: v }))}
                  height="calc(100vh - 360px)"
                  onUploadImage={async (file) => {
                    try {
                      const r = await adminLearnUploadAsset(editingLesson.id, file, 'image');
                      toast.success(t('admin.learning.toastImageInserted'));
                      return `![${file.name}](${r.data.url})`;
                    } catch (err) {
                      toast.error(err.response?.data?.detail || t('admin.learning.toastFailed'));
                      return '';
                    }
                  }}
                  onPickWidget={() => setShowCatalog(true)}
                  onPickExercise={() => setShowExercisePicker(true)}
                />
                {showPreview && (
                  <div
                    className="border border-gray-200 rounded-xl p-4 overflow-auto bg-white dark:bg-slate-900/30 dark:border-slate-700/50"
                    style={{ height: 'calc(100vh - 360px)' }}
                  >
                    <LessonMarkdown>{editorContent}</LessonMarkdown>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
