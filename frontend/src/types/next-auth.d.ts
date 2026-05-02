import NextAuth, { DefaultSession } from "next-auth";
import { JWT } from "next-auth/jwt";

declare module "next-auth" {
  /**
   * Returned by `useSession`, `getSession` and received as a prop on the `SessionProvider` React Context
   */
  interface Session {
    accessToken?: string;
    isAdmin?: boolean;

    graphId?: string;
    user: {
      id?: string;
      address?: string;
    } & DefaultSession["user"];
  }

  interface User {
    graphId?: string;
  }
}

declare module "next-auth/jwt" {
  /** Returned by the `jwt` callback and `getToken`, when using JWT sessions */
  interface JWT {
    accessToken?: string;
    userId?: string;
    isAdmin?: boolean;

    graphId?: string;
  }
}
