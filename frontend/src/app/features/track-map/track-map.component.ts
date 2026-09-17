import { Component, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { Router } from '@angular/router';
import { forkJoin } from 'rxjs';
import { ModuleService, Module as ApiModule } from '../../core/module.service';
import { ProgressService, ModuleProgress } from '../../core/progress.service';
import { DiagnosticService } from '../../core/diagnostic.service';

interface TrackModule {
  id: number;
  title: string;
  status: 'locked' | 'in_progress' | 'completed';
  completionPercentage: number;
}

@Component({
    selector: 'app-track-map',
    templateUrl: './track-map.component.html',
    styleUrls: ['./track-map.component.scss'],
    changeDetection: ChangeDetectionStrategy.Eager,
    standalone: false
})
export class TrackMapComponent implements OnInit {
  modules: TrackModule[] = [];
  loading = true;
  error = '';

  trackId: number | null = null;
  // null = not checked yet; false = never taken; true = already taken.
  diagnosticTaken: boolean | null = null;
  diagnosticDismissed = false;

  constructor(
    private router: Router,
    private moduleService: ModuleService,
    private progressService: ProgressService,
    private diagnosticService: DiagnosticService
  ) { }

  ngOnInit(): void {
    forkJoin({
      modules: this.moduleService.listModules(),
      progress: this.progressService.listProgress(),
    }).subscribe({
      next: ({ modules, progress }) => {
        const progressByModuleId = new Map<number, ModuleProgress>(
          progress.map((p) => [p.module_id, p])
        );
        this.modules = modules.map((m: ApiModule) => {
          const p = progressByModuleId.get(m.id);
          return {
            id: m.id,
            title: m.title,
            status: (p?.status as TrackModule['status']) ?? 'locked',
            completionPercentage: p?.completion_percentage ?? 0,
          };
        });
        this.loading = false;

        if (modules.length > 0) {
          this.trackId = modules[0].track_id;
          this.diagnosticService.getTrackStatus(this.trackId).subscribe({
            next: (status) => (this.diagnosticTaken = status !== null),
            error: () => (this.diagnosticTaken = null),
          });
        }
      },
      error: () => {
        this.error = 'Could not load your learning path. Please try again.';
        this.loading = false;
      },
    });
  }

  get showDiagnosticBanner(): boolean {
    return !this.loading && !this.error && this.diagnosticTaken === false && !this.diagnosticDismissed;
  }

  dismissDiagnosticBanner(): void {
    this.diagnosticDismissed = true;
  }

  goToDiagnostic(): void {
    this.router.navigate(['/dashboard/diagnostic']);
  }

  selectModule(module: TrackModule) {
    this.router.navigate(['/dashboard/module', module.title]);
  }
}
