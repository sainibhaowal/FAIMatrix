import { NextAuthOptions } from "next-auth";
import KeycloakProvider from "next-auth/providers/keycloak";

export const authOptions: NextAuthOptions = {
    providers: [
        KeycloakProvider({
            clientId: process.env.KEYCLOAK_CLIENT_ID || "",
            clientSecret: process.env.KEYCLOAK_CLIENT_SECRET || "",
            issuer: process.env.KEYCLOAK_ISSUER,
        }),
    ],
    session: {
        strategy: "jwt",
    },
    callbacks: {
        async jwt({ token, account }) {
            // Persist the OAuth access_token to the token right after signin
            if (account) {
                token.accessToken = account.access_token;
            }
            return token;
        },
        async session({ session, token }) {
            // Send properties to the client, like an access_token from a provider.
            if (token && typeof token.accessToken === "string") {
                session.accessToken = token.accessToken;
            }
            return session;
        },
    },
};
