import { Component, ChangeDetectionStrategy, OnInit } from '@angular/core';
import { forkJoin } from 'rxjs';
import { AuthService, UserProfile } from '../../core/auth.service';
import { ModuleService, Module as ApiModule } from '../../core/module.service';
import { ProgressService, ModuleProgress } from '../../core/progress.service';
import { DiagnosticService, TopicMastery } from '../../core/diagnostic.service';

interface ModuleSummary {
  id: number;
  title: string;
  status: 'locked' | 'in_progress' | 'completed';
  completionPercentage: number;
  completedLessons: number;
  totalLessons: number;
}

@Component({
  selector: 'app-profile',
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.scss'],
  changeDetection: ChangeDetectionStrategy.Eager,
  standalone: false,
})
export class ProfileComponent implements OnInit {
  loading = true;
  error = '';

  profile: UserProfile | null = null;
  modules: ModuleSummary[] = [];
  mastery: TopicMastery[] = [];
  trackId: number | null = null;

  constructor(
    private authService: AuthService,
    private moduleService: ModuleService,
    private progressService: ProgressService,
    private diagnosticService: DiagnosticService
  ) {}

  ngOnInit(): void {
    forkJoin({
      profile: this.authService.getCurrentUser(),
      modules: this.moduleService.listModules(),
      progress: this.progressService.listProgress(),
    }).subscribe({
      next: ({ profile, modules, progress }) => {
        this.profile = profile;

        const progressByModuleId = new Map<number, ModuleProgress>(
          progress.map((p) => [p.module_id, p])
        );
        this.modules = modules.map((m: ApiModule) => {
          const p = progressByModuleId.get(m.id);
          return {
            id: m.id,
            title: m.title,
            status: (p?.status as ModuleSummary['status']) ?? 'locked',
            completionPercentage: p?.completion_percentage ?? 0,
            completedLessons: p?.completed_lesson_ids.length ?? 0,
            totalLessons: m.lessons.length,
          };
        });

        this.loading = false;

        if (modules.length > 0) {
          this.trackId = modules[0].track_id;
          this.diagnosticService.getTrackMastery(this.trackId).subscribe({
            next: (mastery) => (this.mastery = mastery),
            error: () => (this.mastery = []),
          });
        }
      },
      error: () => {
        this.error = 'Could not load your profile. Please try again.';
        this.loading = false;
      },
    });
  }

  get totalLessons(): number {
    return this.modules.reduce((sum, m) => sum + m.totalLessons, 0);
  }

  get completedLessons(): number {
    return this.modules.reduce((sum, m) => sum + m.completedLessons, 0);
  }

  get overallPercent(): number {
    return this.totalLessons === 0 ? 0 : Math.round((this.completedLessons / this.totalLessons) * 100);
  }

  get modulesCompleted(): number {
    return this.modules.filter((m) => m.status === 'completed').length;
  }

  masteryCount(band: string): number {
    return this.mastery.filter((m) => m.band === band).length;
  }

  bandLabel(band: string): string {
    if (band === 'mastered') return 'Mastered';
    if (band === 'partially_mastered') return 'Partially mastered';
    return 'Needs learning';
  }
}
