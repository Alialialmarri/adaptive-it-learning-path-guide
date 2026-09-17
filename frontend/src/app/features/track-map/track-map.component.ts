import { Component, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { Router } from '@angular/router';
import { forkJoin } from 'rxjs';
import { ModuleService, Module as ApiModule } from '../../core/module.service';
import { ProgressService, ModuleProgress } from '../../core/progress.service';

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

  constructor(
    private router: Router,
    private moduleService: ModuleService,
    private progressService: ProgressService
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
      },
      error: () => {
        this.error = 'Could not load your learning path. Please try again.';
        this.loading = false;
      },
    });
  }

  selectModule(module: TrackModule) {
    this.router.navigate(['/dashboard/module', module.title]);
  }
}
