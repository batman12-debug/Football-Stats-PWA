"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { NavIcon } from "@/components/NavIcon";

interface HeaderNavLinkProps {
  href: string;
  label: string;
  iconSrc: string;
  staticIconSrc?: string;
  exact?: boolean;
  animatedApng?: boolean;
}

export function HeaderNavLink({
  href,
  label,
  iconSrc,
  staticIconSrc,
  exact = false,
  animatedApng = false,
}: HeaderNavLinkProps) {
  const pathname = usePathname();
  const isActive = exact ? pathname === href : pathname.startsWith(href);
  const [isHovered, setIsHovered] = useState(false);

  return (
    <Link
      href={href}
      aria-label={label}
      title={label}
      aria-current={isActive ? "page" : undefined}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onFocus={() => setIsHovered(true)}
      onBlur={() => setIsHovered(false)}
      className={`group inline-flex touch-target items-center justify-center rounded-md p-2 transition-colors sm:min-h-9 sm:min-w-9 sm:p-1.5 ${
        isActive ? "text-white" : "text-muted hover:text-white"
      }`}
    >
      <NavIcon
        src={iconSrc}
        staticSrc={staticIconSrc}
        animatedApng={animatedApng}
        isActive={isActive}
        isHovered={isHovered}
      />
    </Link>
  );
}
