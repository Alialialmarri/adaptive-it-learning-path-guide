import { Component, ChangeDetectionStrategy } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { ProgressService } from '../../core/progress.service';

@Component({
    selector: 'app-login',
    templateUrl: './login.component.html',
    styleUrls: ['./login.component.scss'],
    changeDetection: ChangeDetectionStrategy.Eager,
    standalone: false
})
export class LoginComponent {
  username = '';
  password = '';
  error = '';
  loading = false;

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private auth: AuthService,
    private progressService: ProgressService
  ) {}

  login() {
    this.error = '';
    this.loading = true;
    this.auth.login(this.username, this.password).subscribe({
      next: () => {
        this.loading = false;
        const returnUrl = this.route.snapshot.queryParamMap.get('returnUrl');
        if (returnUrl) {
          // The learner was redirected here from a specific protected page; honor that.
          this.router.navigateByUrl(returnUrl);
          return;
        }

        // FR-08 Resume Learning: default to picking up where the learner left off.
        this.progressService.resume().subscribe({
          next: (resumeModule) => {
            if (resumeModule) {
              this.router.navigate(['/dashboard/module', resumeModule.module_title]);
            } else {
              this.router.navigateByUrl('/dashboard');
            }
          },
          error: () => this.router.navigateByUrl('/dashboard')
        });
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'Invalid credentials';
      }
    });
  }
}
