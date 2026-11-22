import type { ExtendKcContext } from "keycloakify/login";

export type KcContextExtension = {
    themeName: "startech";
    properties: Record<string, string>;
};

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export type KcContextExtensionPerPage = {};

export type KcContext = ExtendKcContext<KcContextExtension, KcContextExtensionPerPage>;
