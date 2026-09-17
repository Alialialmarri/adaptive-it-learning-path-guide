import { Component, OnInit, HostListener, ChangeDetectionStrategy } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ModuleService, Module, Lesson } from '../../core/module.service';
import { ProgressService } from '../../core/progress.service';
import { marked } from 'marked';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

@Component({
    selector: 'app-module-view',
    templateUrl: './module-view.component.html',
    styleUrls: ['./module-view.component.scss'],
    changeDetection: ChangeDetectionStrategy.Eager,
    standalone: false
})
export class ModuleViewComponent implements OnInit {
  module: Module | null = null;
  selectedLesson: Lesson | null = null;
  loading = true;
  error = '';
  isSidebarVisible = true;
  chatPanelWidth = 350;
  minChatWidth = 250;
  maxChatWidth = 800;
  isResizing = false;
  completedLessonIds = new Set<number>();

  constructor(
    private route: ActivatedRoute,
    private moduleService: ModuleService,
    private progressService: ProgressService,
    private sanitizer: DomSanitizer
  ) { }

  ngOnInit(): void {
    const title = this.route.snapshot.paramMap.get('title');
    if (title) {
      this.moduleService.getModuleByTitle(title).subscribe({
        next: (data) => {
          this.module = data;
          this.loading = false;
          if (this.module.lessons && this.module.lessons.length > 0) {
            this.module.lessons.sort((a, b) => a.order - b.order);
            this.selectedLesson = this.module.lessons[0];
            this.loadProgress();
          }
        },
        error: (err) => {
          this.error = 'Failed to load module content.';
          this.loading = false;
          console.error(err);
        }
      });
    } else {
      this.error = 'No module specified.';
      this.loading = false;
    }
  }

  selectLesson(lesson: Lesson): void {
    this.selectedLesson = lesson;
  }

  toggleSidebar(): void {
    this.isSidebarVisible = !this.isSidebarVisible;
  }

  renderMarkdown(content: string | null | undefined): SafeHtml {
    const html = marked.parse(content ?? '') as string;
    return this.sanitizer.bypassSecurityTrustHtml(html);
  }

  isLessonCompleted(lesson: Lesson): boolean {
    return this.completedLessonIds.has(lesson.id);
  }

  toggleLessonCompleted(lesson: Lesson, event?: MouseEvent): void {
    if (event) {
      event.stopPropagation();
    }
    const nowCompleted = !this.completedLessonIds.has(lesson.id);

    // Optimistic UI update; rolled back if the server call fails.
    if (nowCompleted) {
      this.completedLessonIds.add(lesson.id);
    } else {
      this.completedLessonIds.delete(lesson.id);
    }

    this.progressService.setLessonCompletion(lesson.id, nowCompleted).subscribe({
      error: (err) => {
        console.error('Failed to save lesson progress:', err);
        // Roll back the optimistic update on failure.
        if (nowCompleted) {
          this.completedLessonIds.delete(lesson.id);
        } else {
          this.completedLessonIds.add(lesson.id);
        }
      }
    });
  }

  getProgressPercent(): number {
    if (!this.module || !this.module.lessons || this.module.lessons.length === 0) return 0;
    const total = this.module.lessons.length;
    const completed = this.module.lessons.filter(l => this.completedLessonIds.has(l.id)).length;
    return Math.round((completed / total) * 100);
  }

  private loadProgress(): void {
    if (!this.module) return;
    const moduleId = this.module.id;

    // Record that the learner opened this module (for resume-on-login), then
    // load which lessons are already marked complete for this account.
    this.progressService.openModule(moduleId).subscribe({
      next: (progress) => {
        this.completedLessonIds = new Set(progress.completed_lesson_ids);
      },
      error: (err) => {
        console.error('Failed to load module progress:', err);
      }
    });
  }

  startResizing(event: MouseEvent): void {
    event.preventDefault();
    this.isResizing = true;
  }

  @HostListener('document:mousemove', ['$event'])
  onMouseMove(event: MouseEvent): void {
    if (!this.isResizing) return;
    const newWidth = window.innerWidth - event.clientX;
    if (newWidth >= this.minChatWidth && newWidth <= this.maxChatWidth) {
      this.chatPanelWidth = newWidth;
    }
  }

  @HostListener('document:mouseup')
  onMouseUp(): void {
    this.isResizing = false;
  }
}
