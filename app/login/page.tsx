import Link from "next/link";

export const dynamic = "force-dynamic";

export default function LoginPage() {
  return (
    <main className="bg-slate-50 px-4 py-12">
      <div className="mx-auto w-full max-w-md rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-6 py-5">
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
            Land Records Demo Portal
          </p>
          <h1 className="mt-2 text-2xl font-extrabold tracking-tight text-slate-950">
            Registrar Login
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            This is a mock sign-in form for local demo workflows.
          </p>
        </div>

        <form action="/login/submit" method="post" className="space-y-5 px-4 py-6 sm:px-6" noValidate>
          <div className="space-y-1.5">
            <label htmlFor="login-username" className="block text-xs font-bold uppercase tracking-wider text-slate-600">
              Username <span aria-hidden="true" className="text-rose-600">*</span>
            </label>
            <input
              id="login-username"
              name="username"
              type="text"
              required
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none ring-offset-2 focus:ring-2 focus:ring-blue-600 min-h-11"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="login-password" className="block text-xs font-bold uppercase tracking-wider text-slate-600">
              Password <span aria-hidden="true" className="text-rose-600">*</span>
            </label>
            <input
              id="login-password"
              name="password"
              type="password"
              required
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none ring-offset-2 focus:ring-2 focus:ring-blue-600 min-h-11"
            />
          </div>

          <button
            type="submit"
            className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-bold text-white transition-colors hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2 min-h-11"
          >
            Sign in
          </button>
        </form>

        <div className="border-t border-slate-100 px-6 py-4 text-xs text-slate-500">
          <Link href="/" className="font-semibold text-blue-700 hover:underline">
            Back to home
          </Link>
        </div>
      </div>
    </main>
  );
}
