import { Component, ChangeDetectionStrategy } from '@angular/core';
import { AuthService, AuthUser } from '../../core/auth.service';

@Component({
    selector: 'app-dashboard',
    templateUrl: './dashboard.component.html',
    styleUrls: ['./dashboard.component.scss'],
    changeDetection: ChangeDetectionStrategy.Eager,
    standalone: false
})
export class DashboardComponent {
  user: AuthUser | null = null;
  constructor(private auth: AuthService) {
    this.user = this.auth.getUser();
  }
}
