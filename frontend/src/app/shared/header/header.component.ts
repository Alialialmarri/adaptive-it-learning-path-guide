import { Component, ChangeDetectionStrategy, OnInit, OnDestroy } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { Subscription } from 'rxjs';
import { filter } from 'rxjs/operators';
import { AuthService, AuthUser } from '../../core/auth.service';

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss'],
  changeDetection: ChangeDetectionStrategy.Eager,
  standalone: false,
})
export class HeaderComponent implements OnInit, OnDestroy {
  isAuthenticated = false;
  user: AuthUser | null = null;
  private routerSub?: Subscription;

  constructor(private auth: AuthService, private router: Router) {}

  ngOnInit(): void {
    this.refreshAuthState();
    // The header is a single persistent instance across route changes (it
    // lives in app.component, not behind the router-outlet), so it has to
    // re-read auth state on navigation rather than only once at construction
    // -- otherwise it would keep showing "logged out" right after login, or
    // "logged in" right after logout, until some unrelated change detection.
    this.routerSub = this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe(() => this.refreshAuthState());
  }

  ngOnDestroy(): void {
    this.routerSub?.unsubscribe();
  }

  private refreshAuthState(): void {
    this.isAuthenticated = this.auth.isAuthenticated();
    this.user = this.auth.getUser();
  }

  logout(): void {
    this.auth.logout();
    this.refreshAuthState();
    this.router.navigate(['/login']);
  }
}
