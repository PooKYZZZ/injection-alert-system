import Link from "next/link";
import DemoLoginForm from "@/components/DemoLoginForm";

export const dynamic = "force-dynamic";

export default function LoginPage() {
  return (
    <section className="bg-slate-50 px-4 py-12">
      <div className="mx-auto w-full max-w-md rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-6 py-5">
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
            Land Records Demo Portal
          </p>
          <h1 className="mt-2 text-2xl font-extrabold tracking-tight text-slate-950">
            Demo Login
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Authentication is disabled. Use synthetic values to test the login request; no account or session is created.
          </p>
        </div>

        <DemoLoginForm />

        <p className="px-6 pb-4 text-xs text-slate-600">
          The demo records the username for a failed attempt. Passwords are not stored.
        </p>

        <div className="border-t border-slate-100 px-6 py-4 text-xs text-slate-500">
          <Link href="/" className="font-semibold text-blue-700 hover:underline">
            Back to home
          </Link>
        </div>
      </div>
    </section>
  );
}
