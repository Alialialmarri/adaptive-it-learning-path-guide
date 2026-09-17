import { Component, ChangeDetectionStrategy, OnInit } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { ModuleService, Lesson } from '../../core/module.service';
import {
  DiagnosticService,
  DiagnosticQuestion,
  DiagnosticResult,
} from '../../core/diagnostic.service';

interface LessonGroup {
  lessonId: number;
  lessonTitle: string;
  questions: DiagnosticQuestion[];
}

@Component({
  selector: 'app-diagnostic-assessment',
  templateUrl: './diagnostic-assessment.component.html',
  styleUrls: ['./diagnostic-assessment.component.scss'],
  changeDetection: ChangeDetectionStrategy.Eager,
  standalone: false,
})
export class DiagnosticAssessmentComponent implements OnInit {
  state: 'loading' | 'intro' | 'taking' | 'submitting' | 'result' | 'error' = 'loading';
  error = '';

  trackId: number | null = null;
  attemptId: number | null = null;
  lessonGroups: LessonGroup[] = [];
  selectedByQuestion: { [questionId: number]: number } = {};
  result: DiagnosticResult | null = null;
  private lessonTitleById = new Map<number, string>();

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private moduleService: ModuleService,
    private diagnosticService: DiagnosticService
  ) {}

  ngOnInit(): void {
    this.moduleService.listModules().subscribe({
      next: (modules) => {
        if (!modules.length) {
          this.state = 'error';
          this.error = 'No course content is available yet.';
          return;
        }
        this.trackId = modules[0].track_id;
        modules.forEach((m) => m.lessons.forEach((l: Lesson) => this.lessonTitleById.set(l.id, l.title)));
        this.state = 'intro';
      },
      error: () => {
        this.state = 'error';
        this.error = 'Could not load course content. Please try again.';
      },
    });
  }

  startDiagnostic(): void {
    if (this.trackId === null) return;
    this.state = 'loading';
    this.diagnosticService.startTrackDiagnostic(this.trackId).subscribe({
      next: (start) => {
        this.attemptId = start.attempt_id;
        this.lessonGroups = this.groupByLesson(start.questions);
        this.selectedByQuestion = {};
        this.state = 'taking';
      },
      error: () => {
        this.state = 'error';
        this.error =
          'The diagnostic is not available for this course yet (no questions have been authored).';
      },
    });
  }

  private groupByLesson(questions: DiagnosticQuestion[]): LessonGroup[] {
    const groups: LessonGroup[] = [];
    const groupByLessonId = new Map<number, LessonGroup>();
    for (const q of questions) {
      let group = groupByLessonId.get(q.lesson_id);
      if (!group) {
        group = {
          lessonId: q.lesson_id,
          lessonTitle: this.lessonTitleById.get(q.lesson_id) ?? `Topic ${q.lesson_id}`,
          questions: [],
        };
        groupByLessonId.set(q.lesson_id, group);
        groups.push(group);
      }
      group.questions.push(q);
    }
    return groups;
  }

  selectChoice(question: DiagnosticQuestion, choiceIndex: number): void {
    this.selectedByQuestion[question.id] = choiceIndex;
  }

  isSelected(question: DiagnosticQuestion, choiceIndex: number): boolean {
    return this.selectedByQuestion[question.id] === choiceIndex;
  }

  get totalQuestions(): number {
    return this.lessonGroups.reduce((sum, g) => sum + g.questions.length, 0);
  }

  get answeredCount(): number {
    return Object.keys(this.selectedByQuestion).length;
  }

  submit(): void {
    if (this.attemptId === null) return;
    this.state = 'submitting';
    const answers = Object.entries(this.selectedByQuestion).map(([questionId, choice]) => ({
      question_id: Number(questionId),
      selected_choices: [choice],
    }));
    this.diagnosticService.submitDiagnostic(this.attemptId, answers).subscribe({
      next: (result) => {
        this.result = result;
        this.state = 'result';
      },
      error: () => {
        this.state = 'error';
        this.error = 'Could not submit the diagnostic. Please try again.';
      },
    });
  }

  skip(): void {
    this.router.navigate(['/dashboard']);
  }

  bandLabel(band: string): string {
    if (band === 'mastered') return 'Mastered';
    if (band === 'partially_mastered') return 'Partially mastered';
    return 'Needs learning';
  }

  goToRecommendedLesson(): void {
    if (this.result?.recommended_start_module_title) {
      this.router.navigate(['/dashboard/module', this.result.recommended_start_module_title]);
    } else {
      this.router.navigate(['/dashboard']);
    }
  }

  goToDashboard(): void {
    this.router.navigate(['/dashboard']);
  }
}
