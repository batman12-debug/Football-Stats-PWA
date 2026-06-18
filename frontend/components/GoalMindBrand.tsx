import Link from "next/link";

import { GoalMindLogo } from "@/components/GoalMindLogo";

interface GoalMindBrandProps {
  className?: string;
}

export function GoalMindBrand({ className = "" }: GoalMindBrandProps) {
  return (
    <Link
      href="/"
      className={`group flex flex-col items-center gap-1 ${className}`}
    >
      <GoalMindLogo className="h-10 w-auto transition-transform duration-200 group-hover:scale-105 sm:h-11" />
      <span className="font-display type-title text-base sm:text-lg">
        Check<span className="text-win">Board</span>
      </span>
    </Link>
  );
}
