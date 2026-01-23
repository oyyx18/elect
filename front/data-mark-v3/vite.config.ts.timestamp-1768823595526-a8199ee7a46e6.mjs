// vite.config.ts
import process3 from "node:process";
import { URL, fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/vite@5.4.1_@types+node@22.4.1_sass@1.77.8_terser@5.36.0/node_modules/vite/dist/node/index.js";

// build/plugins/index.ts
import vue from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/@vitejs+plugin-vue@5.1.2_vi_a7595c69b530133f844408e4e315ed71/node_modules/@vitejs/plugin-vue/dist/index.mjs";
import vueJsx from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/@vitejs+plugin-vue-jsx@4.0._769f37753ff6ebfb528667835fac9a83/node_modules/@vitejs/plugin-vue-jsx/dist/index.mjs";
import VueDevtools from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/vite-plugin-vue-devtools@7._737c6e1c431c9f1b0dfc466e3bbd960e/node_modules/vite-plugin-vue-devtools/dist/vite.mjs";
import progress from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/vite-plugin-progress@0.0.7__eb20a26ae7094490f4c6c4b8a09a8194/node_modules/vite-plugin-progress/dist/index.mjs";

// build/plugins/router.ts
import ElegantVueRouter from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/@elegant-router+vue@0.3.8/node_modules/@elegant-router/vue/dist/vite.mjs";
function setupElegantRouter() {
  return ElegantVueRouter({
    layouts: {
      base: "src/layouts/base-layout/index.vue",
      blank: "src/layouts/blank-layout/index.vue"
    },
    customRoutes: {
      names: [
        "exception_403",
        "exception_404",
        "exception_500",
        "document_project",
        "document_project-link",
        "document_vue",
        "document_vite",
        "document_unocss",
        "document_naive",
        "document_antd"
      ]
    },
    routePathTransformer(routeName, routePath) {
      const key = routeName;
      if (key === "login") {
        const modules = ["pwd-login", "code-login", "register", "reset-pwd", "bind-wechat"];
        const moduleReg = modules.join("|");
        return `/login/:module(${moduleReg})?`;
      }
      return routePath;
    },
    onRouteMetaGen(routeName) {
      const key = routeName;
      const constantRoutes = ["login", "403", "404", "500"];
      const meta = {
        title: key,
        i18nKey: `route.${key}`
      };
      if (constantRoutes.includes(key)) {
        meta.constant = true;
      }
      return meta;
    }
  });
}

// build/plugins/unocss.ts
import process from "node:process";
import path from "node:path";
import unocss from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/@unocss+vite@0.62.2_rollup@_2d418222afe62450a43d8b0ccb15f24a/node_modules/@unocss/vite/dist/index.mjs";
import presetIcons from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/@unocss+preset-icons@0.62.2/node_modules/@unocss/preset-icons/dist/index.mjs";
import { FileSystemIconLoader } from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/@iconify+utils@2.1.33/node_modules/@iconify/utils/lib/loader/node-loaders.mjs";
function setupUnocss(viteEnv) {
  const { VITE_ICON_PREFIX, VITE_ICON_LOCAL_PREFIX } = viteEnv;
  const localIconPath = path.join(process.cwd(), "src/assets/svg-icon");
  const collectionName = VITE_ICON_LOCAL_PREFIX.replace(`${VITE_ICON_PREFIX}-`, "");
  return unocss({
    presets: [
      presetIcons({
        prefix: `${VITE_ICON_PREFIX}-`,
        scale: 1,
        extraProperties: {
          display: "inline-block"
        },
        collections: {
          [collectionName]: FileSystemIconLoader(
            localIconPath,
            (svg) => svg.replace(/^<svg\s/, '<svg width="1em" height="1em" ')
          )
        },
        warn: true
      })
    ]
  });
}

// build/plugins/unplugin.ts
import process2 from "node:process";
import path2 from "node:path";
import Icons from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/unplugin-icons@0.19.2_@vue+_2cc6579c1f7175a24d9d61d23ed2a4bd/node_modules/unplugin-icons/dist/vite.js";
import IconsResolver from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/unplugin-icons@0.19.2_@vue+_2cc6579c1f7175a24d9d61d23ed2a4bd/node_modules/unplugin-icons/dist/resolver.js";
import Components from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/unplugin-vue-components@0.2_f7942e43f7139adc08b4c6c80b8793cf/node_modules/unplugin-vue-components/dist/vite.js";
import { AntDesignVueResolver, NaiveUiResolver } from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/unplugin-vue-components@0.2_f7942e43f7139adc08b4c6c80b8793cf/node_modules/unplugin-vue-components/dist/resolvers.js";
import { FileSystemIconLoader as FileSystemIconLoader2 } from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/unplugin-icons@0.19.2_@vue+_2cc6579c1f7175a24d9d61d23ed2a4bd/node_modules/unplugin-icons/dist/loaders.js";
import { createSvgIconsPlugin } from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/vite-plugin-svg-icons@2.0.1_f0e8aaaad1f72228196f1aee8f64cab0/node_modules/vite-plugin-svg-icons/dist/index.mjs";
function setupUnplugin(viteEnv) {
  const { VITE_ICON_PREFIX, VITE_ICON_LOCAL_PREFIX } = viteEnv;
  const localIconPath = path2.join(process2.cwd(), "src/assets/svg-icon");
  const collectionName = VITE_ICON_LOCAL_PREFIX.replace(`${VITE_ICON_PREFIX}-`, "");
  const plugins = [
    Icons({
      compiler: "vue3",
      customCollections: {
        [collectionName]: FileSystemIconLoader2(
          localIconPath,
          (svg) => svg.replace(/^<svg\s/, '<svg width="1em" height="1em" ')
        )
      },
      scale: 1,
      defaultClass: "inline-block"
    }),
    Components({
      dts: "src/typings/components.d.ts",
      types: [{ from: "vue-router", names: ["RouterLink", "RouterView"] }],
      resolvers: [
        AntDesignVueResolver({
          importStyle: false
        }),
        NaiveUiResolver(),
        IconsResolver({ customCollections: [collectionName], componentPrefix: VITE_ICON_PREFIX })
      ]
    }),
    createSvgIconsPlugin({
      iconDirs: [localIconPath],
      symbolId: `${VITE_ICON_LOCAL_PREFIX}-[dir]-[name]`,
      inject: "body-last",
      customDomId: "__SVG_ICON_LOCAL__"
    })
  ];
  return plugins;
}

// build/plugins/html.ts
function setupHtmlPlugin(buildTime) {
  const plugin = {
    name: "html-plugin",
    apply: "build",
    transformIndexHtml(html) {
      return html.replace("<head>", `<head>
    <meta name="buildTime" content="${buildTime}">`);
    }
  };
  return plugin;
}

// build/plugins/index.ts
import AutoImport from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/unplugin-auto-import@0.18.3_49bc9daa59a7cda8e6ab2eeb113ad61d/node_modules/unplugin-auto-import/dist/vite.js";
import { visualizer } from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/rollup-plugin-visualizer@5.12.0_rollup@4.24.2/node_modules/rollup-plugin-visualizer/dist/plugin/index.js";
import viteImagemin from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/vite-plugin-imagemin@0.6.1__33a23696b87e091f3169279273b101af/node_modules/vite-plugin-imagemin/dist/index.mjs";
import viteCompression from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/vite-plugin-compression@0.5_c96a536c79f55a9b17b71b599b405789/node_modules/vite-plugin-compression/dist/index.mjs";
function setupVitePlugins(viteEnv, buildTime) {
  const plugins = [
    vue({
      script: {
        defineModel: true
      }
    }),
    vueJsx(),
    AutoImport({
      imports: ["vue", "vue-router", "pinia"],
      // 自动引入的三方库
      dts: "src/typings/auto-import.d.ts",
      // 全局自动引入文件存放路径；不配置保存在根目录下；配置为false时将不会生成 auto-imports.d.ts 文件（不影响效果）
      eslintrc: {
        // 项目中使用了 eslint，那么虽然可以正常使用 API 了，但是 eslint 还是会报没有引入的报错。下面的配置可以处理这种情况
        enabled: true
        // 会在根目录下自动生成 .eslintrc-auto-import.json 文件
      }
    }),
    VueDevtools(),
    setupElegantRouter(),
    setupUnocss(viteEnv),
    ...setupUnplugin(viteEnv),
    progress(),
    setupHtmlPlugin(buildTime),
    // 调优
    visualizer({ open: false }),
    viteImagemin({
      // 无损压缩配置，无损压缩下图片质量不会变差
      optipng: {
        optimizationLevel: 7
      },
      // 有损压缩配置，有损压缩下图片质量可能会变差
      pngquant: {
        quality: [0.8, 0.9]
      },
      // svg 优化
      svgo: {
        plugins: [
          {
            name: "removeViewBox"
          },
          {
            name: "removeEmptyAttrs",
            active: false
          }
        ]
      }
    }),
    viteCompression({
      verbose: true,
      // 默认即可
      disable: false,
      // 开启压缩(不禁用)，默认即可
      deleteOriginFile: false,
      // 删除源文件
      threshold: 5120,
      // 压缩前最小文件大小
      algorithm: "gzip",
      // 压缩算法
      ext: ".gz"
      // 文件类型
    })
  ];
  return plugins;
}

// src/utils/service.ts
function createServiceConfig(env) {
  const { VITE_SERVICE_BASE_URL, VITE_OTHER_SERVICE_BASE_URL } = env;
  let other = {};
  try {
    other = JSON.parse(VITE_OTHER_SERVICE_BASE_URL);
  } catch (error) {
    console.error("VITE_OTHER_SERVICE_BASE_URL is not a valid JSON string");
  }
  const httpConfig = {
    baseURL: VITE_SERVICE_BASE_URL,
    other
  };
  const otherHttpKeys = Object.keys(httpConfig.other);
  const otherConfig = otherHttpKeys.map((key) => {
    return {
      key,
      baseURL: httpConfig.other[key],
      proxyPattern: createProxyPattern(key)
    };
  });
  const config = {
    baseURL: httpConfig.baseURL,
    proxyPattern: createProxyPattern(),
    other: otherConfig
  };
  return config;
}
function createProxyPattern(key) {
  if (!key) {
    return "/proxy-default";
  }
  return `/proxy-${key}`;
}

// build/config/proxy.ts
function createViteProxy(env, isDev) {
  const isEnableHttpProxy = isDev && env.VITE_HTTP_PROXY === "Y";
  if (!isEnableHttpProxy) return void 0;
  const { baseURL, proxyPattern, other } = createServiceConfig(env);
  const proxy = createProxyItem({
    baseURL,
    proxyPattern
  });
  other.forEach((item) => {
    Object.assign(proxy, createProxyItem(item));
  });
  return proxy;
}
function createProxyItem(item) {
  const proxy = {};
  proxy[item.proxyPattern] = {
    target: item.baseURL,
    changeOrigin: true,
    rewrite: (path3) => path3.replace(new RegExp(`^${item.proxyPattern}`), "")
  };
  return proxy;
}

// build/config/time.ts
import dayjs from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/dayjs@1.11.12/node_modules/dayjs/dayjs.min.js";
import utc from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/dayjs@1.11.12/node_modules/dayjs/plugin/utc.js";
import timezone from "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/node_modules/.pnpm/dayjs@1.11.12/node_modules/dayjs/plugin/timezone.js";
function getBuildTime() {
  dayjs.extend(utc);
  dayjs.extend(timezone);
  const buildTime = dayjs.tz(Date.now(), "Asia/Shanghai").format("YYYY-MM-DD HH:mm:ss");
  return buildTime;
}

// vite.config.ts
var __vite_injected_original_import_meta_url = "file:///D:/PROJECT/ELEC_1126/front/data-mark-v3/vite.config.ts";
var vite_config_default = defineConfig((configEnv) => {
  const viteEnv = loadEnv(
    configEnv.mode,
    process3.cwd()
  );
  const buildTime = getBuildTime();
  const enableProxy = configEnv.command === "serve" && !configEnv.isPreview;
  return {
    base: viteEnv.VITE_BASE_URL,
    resolve: {
      alias: {
        "~": fileURLToPath(new URL("./", __vite_injected_original_import_meta_url)),
        "@": fileURLToPath(new URL("./src", __vite_injected_original_import_meta_url)),
        "@vue-office/excel": "@vue-office/excel"
        // 根据实际入口文件路径调整
      }
    },
    css: {
      preprocessorOptions: {
        scss: {
          additionalData: `@use "./src/styles/scss/global.scss" as *;`
        }
      }
    },
    plugins: setupVitePlugins(viteEnv, buildTime),
    define: {
      BUILD_TIME: JSON.stringify(buildTime)
    },
    server: {
      host: "0.0.0.0",
      port: 8080,
      open: true,
      proxy: createViteProxy(viteEnv, enableProxy),
      fs: {
        cachedChecks: false
      }
    },
    preview: {
      port: 9725
    },
    build: {
      reportCompressedSize: false,
      sourcemap: viteEnv.VITE_SOURCE_MAP === "Y",
      commonjsOptions: {
        ignoreTryCatch: false
      },
      rollupOptions: {
        output: {
          chunkFileNames: "js/[name]-[hash].js",
          // 引入文件名的名称
          entryFileNames: "js/[name]-[hash].js",
          // 包的入口文件名称
          // assetFileNames: "[ext]/[name]-[hash].[ext]", // 资源文件像字体，图片等
          // 对打包出来的资源文件进行分类，分别放到不同的文件夹内
          assetFileNames(assetsInfo) {
            if (assetsInfo.name?.endsWith(".css")) {
              return "css/[name]-[hash].css";
            }
            const fontExts = [".ttf", ".otf", ".woff", ".woff2", ".eot"];
            if (fontExts.some((ext) => assetsInfo.name?.endsWith(ext))) {
              return "font/[name]-[hash].[ext]";
            }
            const imgExts = [".png", ".jpg", ".jpeg", ".webp", ".gif", ".icon"];
            if (imgExts.some((ext) => assetsInfo.name?.endsWith(ext))) {
              return "img/[name]-[hash].[ext]";
            }
            const imgSvg = [".svg"];
            if (imgSvg.some((ext) => assetsInfo.name?.endsWith(ext))) {
              return "assest/icons/[name].[ext]";
            }
            const videoExts = [".mp4", ".avi", ".wmv", ".ram", ".mpg", "mpeg"];
            if (videoExts.some((ext) => assetsInfo.name?.endsWith(ext))) {
              return "video/[name]-[hash].[ext]";
            }
            return "assets/[name]-[hash].[ext]";
          },
          manualChunks(id) {
            if (id.includes("node_modules")) {
              return id.toString().split("node_modules/")[1].split("/")[0].toString();
            }
          }
        }
      },
      // 打包环境移除console.log，debugger
      terserOptions: {
        compress: {
          drop_console: true,
          drop_debugger: true
        }
      }
    }
  };
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiLCAiYnVpbGQvcGx1Z2lucy9pbmRleC50cyIsICJidWlsZC9wbHVnaW5zL3JvdXRlci50cyIsICJidWlsZC9wbHVnaW5zL3Vub2Nzcy50cyIsICJidWlsZC9wbHVnaW5zL3VucGx1Z2luLnRzIiwgImJ1aWxkL3BsdWdpbnMvaHRtbC50cyIsICJzcmMvdXRpbHMvc2VydmljZS50cyIsICJidWlsZC9jb25maWcvcHJveHkudHMiLCAiYnVpbGQvY29uZmlnL3RpbWUudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJEOlxcXFxQUk9KRUNUXFxcXEVMRUNfMTEyNlxcXFxmcm9udFxcXFxkYXRhLW1hcmstdjNcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIkQ6XFxcXFBST0pFQ1RcXFxcRUxFQ18xMTI2XFxcXGZyb250XFxcXGRhdGEtbWFyay12M1xcXFx2aXRlLmNvbmZpZy50c1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vRDovUFJPSkVDVC9FTEVDXzExMjYvZnJvbnQvZGF0YS1tYXJrLXYzL3ZpdGUuY29uZmlnLnRzXCI7aW1wb3J0IHByb2Nlc3MgZnJvbSBcIm5vZGU6cHJvY2Vzc1wiO1xuaW1wb3J0IHsgVVJMLCBmaWxlVVJMVG9QYXRoIH0gZnJvbSBcIm5vZGU6dXJsXCI7XG5pbXBvcnQgeyBkZWZpbmVDb25maWcsIGxvYWRFbnYgfSBmcm9tIFwidml0ZVwiO1xuaW1wb3J0IHsgc2V0dXBWaXRlUGx1Z2lucyB9IGZyb20gXCIuL2J1aWxkL3BsdWdpbnNcIjtcbmltcG9ydCB7IGNyZWF0ZVZpdGVQcm94eSwgZ2V0QnVpbGRUaW1lIH0gZnJvbSBcIi4vYnVpbGQvY29uZmlnXCI7XG5cbmV4cG9ydCBkZWZhdWx0IGRlZmluZUNvbmZpZygoY29uZmlnRW52KSA9PiB7XG4gIGNvbnN0IHZpdGVFbnYgPSBsb2FkRW52KFxuICAgIGNvbmZpZ0Vudi5tb2RlLFxuICAgIHByb2Nlc3MuY3dkKCksXG4gICkgYXMgdW5rbm93biBhcyBFbnYuSW1wb3J0TWV0YTtcblxuICBjb25zdCBidWlsZFRpbWUgPSBnZXRCdWlsZFRpbWUoKTtcblxuICBjb25zdCBlbmFibGVQcm94eSA9IGNvbmZpZ0Vudi5jb21tYW5kID09PSBcInNlcnZlXCIgJiYgIWNvbmZpZ0Vudi5pc1ByZXZpZXc7XG5cbiAgcmV0dXJuIHtcbiAgICBiYXNlOiB2aXRlRW52LlZJVEVfQkFTRV9VUkwsXG4gICAgcmVzb2x2ZToge1xuICAgICAgYWxpYXM6IHtcbiAgICAgICAgXCJ+XCI6IGZpbGVVUkxUb1BhdGgobmV3IFVSTChcIi4vXCIsIGltcG9ydC5tZXRhLnVybCkpLFxuICAgICAgICBcIkBcIjogZmlsZVVSTFRvUGF0aChuZXcgVVJMKFwiLi9zcmNcIiwgaW1wb3J0Lm1ldGEudXJsKSksXG4gICAgICAgICdAdnVlLW9mZmljZS9leGNlbCc6ICdAdnVlLW9mZmljZS9leGNlbCcgLy8gXHU2ODM5XHU2MzZFXHU1QjlFXHU5NjQ1XHU1MTY1XHU1M0UzXHU2NTg3XHU0RUY2XHU4REVGXHU1Rjg0XHU4QzAzXHU2NTc0XG4gICAgICB9LFxuICAgIH0sXG4gICAgY3NzOiB7XG4gICAgICBwcmVwcm9jZXNzb3JPcHRpb25zOiB7XG4gICAgICAgIHNjc3M6IHtcbiAgICAgICAgICBhZGRpdGlvbmFsRGF0YTogYEB1c2UgXCIuL3NyYy9zdHlsZXMvc2Nzcy9nbG9iYWwuc2Nzc1wiIGFzICo7YCxcbiAgICAgICAgfSxcbiAgICAgIH0sXG4gICAgfSxcbiAgICBwbHVnaW5zOiBzZXR1cFZpdGVQbHVnaW5zKHZpdGVFbnYsIGJ1aWxkVGltZSksXG4gICAgZGVmaW5lOiB7XG4gICAgICBCVUlMRF9USU1FOiBKU09OLnN0cmluZ2lmeShidWlsZFRpbWUpLFxuICAgIH0sXG4gICAgc2VydmVyOiB7XG4gICAgICBob3N0OiBcIjAuMC4wLjBcIixcbiAgICAgIHBvcnQ6IDgwODAsXG4gICAgICBvcGVuOiB0cnVlLFxuICAgICAgcHJveHk6IGNyZWF0ZVZpdGVQcm94eSh2aXRlRW52LCBlbmFibGVQcm94eSksXG4gICAgICBmczoge1xuICAgICAgICBjYWNoZWRDaGVja3M6IGZhbHNlLFxuICAgICAgfSxcbiAgICB9LFxuICAgIHByZXZpZXc6IHtcbiAgICAgIHBvcnQ6IDk3MjUsXG4gICAgfSxcbiAgICBidWlsZDoge1xuICAgICAgcmVwb3J0Q29tcHJlc3NlZFNpemU6IGZhbHNlLFxuICAgICAgc291cmNlbWFwOiB2aXRlRW52LlZJVEVfU09VUkNFX01BUCA9PT0gXCJZXCIsXG4gICAgICBjb21tb25qc09wdGlvbnM6IHtcbiAgICAgICAgaWdub3JlVHJ5Q2F0Y2g6IGZhbHNlLFxuICAgICAgfSxcbiAgICAgIHJvbGx1cE9wdGlvbnM6IHtcbiAgICAgICAgb3V0cHV0OiB7XG4gICAgICAgICAgY2h1bmtGaWxlTmFtZXM6IFwianMvW25hbWVdLVtoYXNoXS5qc1wiLCAvLyBcdTVGMTVcdTUxNjVcdTY1ODdcdTRFRjZcdTU0MERcdTc2ODRcdTU0MERcdTc5RjBcbiAgICAgICAgICBlbnRyeUZpbGVOYW1lczogXCJqcy9bbmFtZV0tW2hhc2hdLmpzXCIsIC8vIFx1NTMwNVx1NzY4NFx1NTE2NVx1NTNFM1x1NjU4N1x1NEVGNlx1NTQwRFx1NzlGMFxuICAgICAgICAgIC8vIGFzc2V0RmlsZU5hbWVzOiBcIltleHRdL1tuYW1lXS1baGFzaF0uW2V4dF1cIiwgLy8gXHU4RDQ0XHU2RTkwXHU2NTg3XHU0RUY2XHU1MENGXHU1QjU3XHU0RjUzXHVGRjBDXHU1NkZFXHU3MjQ3XHU3QjQ5XG4gICAgICAgICAgLy8gXHU1QkY5XHU2MjUzXHU1MzA1XHU1MUZBXHU2NzY1XHU3Njg0XHU4RDQ0XHU2RTkwXHU2NTg3XHU0RUY2XHU4RkRCXHU4ODRDXHU1MjA2XHU3QzdCXHVGRjBDXHU1MjA2XHU1MjJCXHU2NTNFXHU1MjMwXHU0RTBEXHU1NDBDXHU3Njg0XHU2NTg3XHU0RUY2XHU1OTM5XHU1MTg1XG4gICAgICAgICAgYXNzZXRGaWxlTmFtZXMoYXNzZXRzSW5mbykge1xuICAgICAgICAgICAgLy8gIGNzc1x1NjgzN1x1NUYwRlx1NjU4N1x1NEVGNlxuICAgICAgICAgICAgaWYgKGFzc2V0c0luZm8ubmFtZT8uZW5kc1dpdGgoXCIuY3NzXCIpKSB7XG4gICAgICAgICAgICAgIHJldHVybiBcImNzcy9bbmFtZV0tW2hhc2hdLmNzc1wiO1xuICAgICAgICAgICAgfVxuICAgICAgICAgICAgLy8gIFx1NUI1N1x1NEY1M1x1NjU4N1x1NEVGNlxuICAgICAgICAgICAgY29uc3QgZm9udEV4dHMgPSBbXCIudHRmXCIsIFwiLm90ZlwiLCBcIi53b2ZmXCIsIFwiLndvZmYyXCIsIFwiLmVvdFwiXTtcbiAgICAgICAgICAgIGlmIChmb250RXh0cy5zb21lKChleHQpID0+IGFzc2V0c0luZm8ubmFtZT8uZW5kc1dpdGgoZXh0KSkpIHtcbiAgICAgICAgICAgICAgcmV0dXJuIFwiZm9udC9bbmFtZV0tW2hhc2hdLltleHRdXCI7XG4gICAgICAgICAgICB9XG5cbiAgICAgICAgICAgIC8vICBcdTU2RkVcdTcyNDdcdTY1ODdcdTRFRjZcbiAgICAgICAgICAgIGNvbnN0IGltZ0V4dHMgPSBbXCIucG5nXCIsIFwiLmpwZ1wiLCBcIi5qcGVnXCIsIFwiLndlYnBcIiwgXCIuZ2lmXCIsIFwiLmljb25cIl07XG4gICAgICAgICAgICBpZiAoaW1nRXh0cy5zb21lKChleHQpID0+IGFzc2V0c0luZm8ubmFtZT8uZW5kc1dpdGgoZXh0KSkpIHtcbiAgICAgICAgICAgICAgcmV0dXJuIFwiaW1nL1tuYW1lXS1baGFzaF0uW2V4dF1cIjtcbiAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgLy8gIFNWR1x1N0M3Qlx1NTc4Qlx1NzY4NFx1NTZGRVx1NzI0N1x1NjU4N1x1NEVGNlxuICAgICAgICAgICAgY29uc3QgaW1nU3ZnID0gW1wiLnN2Z1wiXTtcbiAgICAgICAgICAgIGlmIChpbWdTdmcuc29tZSgoZXh0KSA9PiBhc3NldHNJbmZvLm5hbWU/LmVuZHNXaXRoKGV4dCkpKSB7XG4gICAgICAgICAgICAgIHJldHVybiBcImFzc2VzdC9pY29ucy9bbmFtZV0uW2V4dF1cIjtcbiAgICAgICAgICAgIH1cblxuICAgICAgICAgICAgLy8gIFx1ODlDNlx1OTg5MVx1NjU4N1x1NEVGNlxuICAgICAgICAgICAgY29uc3QgdmlkZW9FeHRzID0gW1wiLm1wNFwiLCBcIi5hdmlcIiwgXCIud212XCIsIFwiLnJhbVwiLCBcIi5tcGdcIiwgXCJtcGVnXCJdO1xuICAgICAgICAgICAgaWYgKHZpZGVvRXh0cy5zb21lKChleHQpID0+IGFzc2V0c0luZm8ubmFtZT8uZW5kc1dpdGgoZXh0KSkpIHtcbiAgICAgICAgICAgICAgcmV0dXJuIFwidmlkZW8vW25hbWVdLVtoYXNoXS5bZXh0XVwiO1xuICAgICAgICAgICAgfVxuICAgICAgICAgICAgLy8gIFx1NTE3Nlx1NUI4M1x1NjU4N1x1NEVGNjogXHU0RkREXHU1QjU4XHU1NzI4IGFzc2V0cy9cdTU2RkVcdTcyNDdcdTU0MEQtXHU1NEM4XHU1RTBDXHU1MDNDLlx1NjI2OVx1NUM1NVx1NTQwRFxuICAgICAgICAgICAgcmV0dXJuIFwiYXNzZXRzL1tuYW1lXS1baGFzaF0uW2V4dF1cIjtcbiAgICAgICAgICB9LFxuICAgICAgICAgIG1hbnVhbENodW5rcyhpZCkge1xuICAgICAgICAgICAgaWYgKGlkLmluY2x1ZGVzKFwibm9kZV9tb2R1bGVzXCIpKSB7XG4gICAgICAgICAgICAgIHJldHVybiBpZFxuICAgICAgICAgICAgICAgIC50b1N0cmluZygpXG4gICAgICAgICAgICAgICAgLnNwbGl0KFwibm9kZV9tb2R1bGVzL1wiKVsxXVxuICAgICAgICAgICAgICAgIC5zcGxpdChcIi9cIilbMF1cbiAgICAgICAgICAgICAgICAudG9TdHJpbmcoKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9LFxuICAgICAgICB9LFxuICAgICAgfSxcbiAgICAgIC8vIFx1NjI1M1x1NTMwNVx1NzNBRlx1NTg4M1x1NzlGQlx1OTY2NGNvbnNvbGUubG9nXHVGRjBDZGVidWdnZXJcbiAgICAgIHRlcnNlck9wdGlvbnM6IHtcbiAgICAgICAgY29tcHJlc3M6IHtcbiAgICAgICAgICBkcm9wX2NvbnNvbGU6IHRydWUsXG4gICAgICAgICAgZHJvcF9kZWJ1Z2dlcjogdHJ1ZSxcbiAgICAgICAgfSxcbiAgICAgIH0sXG4gICAgfSxcbiAgfTtcbn0pO1xuIiwgImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJEOlxcXFxQUk9KRUNUXFxcXEVMRUNfMTEyNlxcXFxmcm9udFxcXFxkYXRhLW1hcmstdjNcXFxcYnVpbGRcXFxccGx1Z2luc1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9maWxlbmFtZSA9IFwiRDpcXFxcUFJPSkVDVFxcXFxFTEVDXzExMjZcXFxcZnJvbnRcXFxcZGF0YS1tYXJrLXYzXFxcXGJ1aWxkXFxcXHBsdWdpbnNcXFxcaW5kZXgudHNcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfaW1wb3J0X21ldGFfdXJsID0gXCJmaWxlOi8vL0Q6L1BST0pFQ1QvRUxFQ18xMTI2L2Zyb250L2RhdGEtbWFyay12My9idWlsZC9wbHVnaW5zL2luZGV4LnRzXCI7aW1wb3J0IHR5cGUgeyBQbHVnaW5PcHRpb24gfSBmcm9tIFwidml0ZVwiO1xuaW1wb3J0IHZ1ZSBmcm9tIFwiQHZpdGVqcy9wbHVnaW4tdnVlXCI7XG5pbXBvcnQgdnVlSnN4IGZyb20gXCJAdml0ZWpzL3BsdWdpbi12dWUtanN4XCI7XG5pbXBvcnQgVnVlRGV2dG9vbHMgZnJvbSBcInZpdGUtcGx1Z2luLXZ1ZS1kZXZ0b29sc1wiO1xuaW1wb3J0IHByb2dyZXNzIGZyb20gXCJ2aXRlLXBsdWdpbi1wcm9ncmVzc1wiO1xuaW1wb3J0IHsgc2V0dXBFbGVnYW50Um91dGVyIH0gZnJvbSBcIi4vcm91dGVyXCI7XG5pbXBvcnQgeyBzZXR1cFVub2NzcyB9IGZyb20gXCIuL3Vub2Nzc1wiO1xuaW1wb3J0IHsgc2V0dXBVbnBsdWdpbiB9IGZyb20gXCIuL3VucGx1Z2luXCI7XG5pbXBvcnQgeyBzZXR1cEh0bWxQbHVnaW4gfSBmcm9tIFwiLi9odG1sXCI7XG5pbXBvcnQgQXV0b0ltcG9ydCBmcm9tIFwidW5wbHVnaW4tYXV0by1pbXBvcnQvdml0ZVwiO1xuLy8gXHU0RjE4XHU1MzE2XG5pbXBvcnQgeyB2aXN1YWxpemVyIH0gZnJvbSBcInJvbGx1cC1wbHVnaW4tdmlzdWFsaXplclwiO1xuaW1wb3J0IHZpdGVJbWFnZW1pbiBmcm9tIFwidml0ZS1wbHVnaW4taW1hZ2VtaW5cIjtcbmltcG9ydCB2aXRlQ29tcHJlc3Npb24gZnJvbSBcInZpdGUtcGx1Z2luLWNvbXByZXNzaW9uXCI7XG5cbmV4cG9ydCBmdW5jdGlvbiBzZXR1cFZpdGVQbHVnaW5zKHZpdGVFbnY6IEVudi5JbXBvcnRNZXRhLCBidWlsZFRpbWU6IHN0cmluZykge1xuICBjb25zdCBwbHVnaW5zOiBQbHVnaW5PcHRpb24gPSBbXG4gICAgdnVlKHtcbiAgICAgIHNjcmlwdDoge1xuICAgICAgICBkZWZpbmVNb2RlbDogdHJ1ZSxcbiAgICAgIH0sXG4gICAgfSksXG4gICAgdnVlSnN4KCksXG4gICAgQXV0b0ltcG9ydCh7XG4gICAgICBpbXBvcnRzOiBbXCJ2dWVcIiwgXCJ2dWUtcm91dGVyXCIsIFwicGluaWFcIl0sIC8vIFx1ODFFQVx1NTJBOFx1NUYxNVx1NTE2NVx1NzY4NFx1NEUwOVx1NjVCOVx1NUU5M1xuICAgICAgZHRzOiBcInNyYy90eXBpbmdzL2F1dG8taW1wb3J0LmQudHNcIiwgLy8gXHU1MTY4XHU1QzQwXHU4MUVBXHU1MkE4XHU1RjE1XHU1MTY1XHU2NTg3XHU0RUY2XHU1QjU4XHU2NTNFXHU4REVGXHU1Rjg0XHVGRjFCXHU0RTBEXHU5MTREXHU3RjZFXHU0RkREXHU1QjU4XHU1NzI4XHU2ODM5XHU3NkVFXHU1RjU1XHU0RTBCXHVGRjFCXHU5MTREXHU3RjZFXHU0RTNBZmFsc2VcdTY1RjZcdTVDMDZcdTRFMERcdTRGMUFcdTc1MUZcdTYyMTAgYXV0by1pbXBvcnRzLmQudHMgXHU2NTg3XHU0RUY2XHVGRjA4XHU0RTBEXHU1RjcxXHU1NENEXHU2NTQ4XHU2NzlDXHVGRjA5XG4gICAgICBlc2xpbnRyYzoge1xuICAgICAgICAvLyBcdTk4NzlcdTc2RUVcdTRFMkRcdTRGN0ZcdTc1MjhcdTRFODYgZXNsaW50XHVGRjBDXHU5MEEzXHU0RTQ4XHU4NjdEXHU3MTM2XHU1M0VGXHU0RUU1XHU2QjYzXHU1RTM4XHU0RjdGXHU3NTI4IEFQSSBcdTRFODZcdUZGMENcdTRGNDZcdTY2MkYgZXNsaW50IFx1OEZEOFx1NjYyRlx1NEYxQVx1NjJBNVx1NkNBMVx1NjcwOVx1NUYxNVx1NTE2NVx1NzY4NFx1NjJBNVx1OTUxOVx1MzAwMlx1NEUwQlx1OTc2Mlx1NzY4NFx1OTE0RFx1N0Y2RVx1NTNFRlx1NEVFNVx1NTkwNFx1NzQwNlx1OEZEOVx1NzlDRFx1NjBDNVx1NTFCNVxuICAgICAgICBlbmFibGVkOiB0cnVlLCAvLyBcdTRGMUFcdTU3MjhcdTY4MzlcdTc2RUVcdTVGNTVcdTRFMEJcdTgxRUFcdTUyQThcdTc1MUZcdTYyMTAgLmVzbGludHJjLWF1dG8taW1wb3J0Lmpzb24gXHU2NTg3XHU0RUY2XG4gICAgICB9LFxuICAgIH0pLFxuICAgIFZ1ZURldnRvb2xzKCksXG4gICAgc2V0dXBFbGVnYW50Um91dGVyKCksXG4gICAgc2V0dXBVbm9jc3Modml0ZUVudiksXG4gICAgLi4uc2V0dXBVbnBsdWdpbih2aXRlRW52KSxcbiAgICBwcm9ncmVzcygpLFxuICAgIHNldHVwSHRtbFBsdWdpbihidWlsZFRpbWUpLFxuICAgIC8vIFx1OEMwM1x1NEYxOFxuICAgIHZpc3VhbGl6ZXIoeyBvcGVuOiBmYWxzZSB9KSxcbiAgICB2aXRlSW1hZ2VtaW4oe1xuICAgICAgLy8gXHU2NUUwXHU2MzVGXHU1MzhCXHU3RjI5XHU5MTREXHU3RjZFXHVGRjBDXHU2NUUwXHU2MzVGXHU1MzhCXHU3RjI5XHU0RTBCXHU1NkZFXHU3MjQ3XHU4RDI4XHU5MUNGXHU0RTBEXHU0RjFBXHU1M0Q4XHU1REVFXG4gICAgICBvcHRpcG5nOiB7XG4gICAgICAgIG9wdGltaXphdGlvbkxldmVsOiA3LFxuICAgICAgfSxcbiAgICAgIC8vIFx1NjcwOVx1NjM1Rlx1NTM4Qlx1N0YyOVx1OTE0RFx1N0Y2RVx1RkYwQ1x1NjcwOVx1NjM1Rlx1NTM4Qlx1N0YyOVx1NEUwQlx1NTZGRVx1NzI0N1x1OEQyOFx1OTFDRlx1NTNFRlx1ODBGRFx1NEYxQVx1NTNEOFx1NURFRVxuICAgICAgcG5ncXVhbnQ6IHtcbiAgICAgICAgcXVhbGl0eTogWzAuOCwgMC45XSxcbiAgICAgIH0sXG4gICAgICAvLyBzdmcgXHU0RjE4XHU1MzE2XG4gICAgICBzdmdvOiB7XG4gICAgICAgIHBsdWdpbnM6IFtcbiAgICAgICAgICB7XG4gICAgICAgICAgICBuYW1lOiBcInJlbW92ZVZpZXdCb3hcIixcbiAgICAgICAgICB9LFxuICAgICAgICAgIHtcbiAgICAgICAgICAgIG5hbWU6IFwicmVtb3ZlRW1wdHlBdHRyc1wiLFxuICAgICAgICAgICAgYWN0aXZlOiBmYWxzZSxcbiAgICAgICAgICB9LFxuICAgICAgICBdLFxuICAgICAgfSxcbiAgICB9KSxcbiAgICB2aXRlQ29tcHJlc3Npb24oe1xuICAgICAgdmVyYm9zZTogdHJ1ZSwgLy8gXHU5RUQ4XHU4QkE0XHU1MzczXHU1M0VGXG4gICAgICBkaXNhYmxlOiBmYWxzZSwgLy8gXHU1RjAwXHU1NDJGXHU1MzhCXHU3RjI5KFx1NEUwRFx1Nzk4MVx1NzUyOClcdUZGMENcdTlFRDhcdThCQTRcdTUzNzNcdTUzRUZcbiAgICAgIGRlbGV0ZU9yaWdpbkZpbGU6IGZhbHNlLCAvLyBcdTUyMjBcdTk2NjRcdTZFOTBcdTY1ODdcdTRFRjZcbiAgICAgIHRocmVzaG9sZDogNTEyMCwgLy8gXHU1MzhCXHU3RjI5XHU1MjREXHU2NzAwXHU1QzBGXHU2NTg3XHU0RUY2XHU1OTI3XHU1QzBGXG4gICAgICBhbGdvcml0aG06IFwiZ3ppcFwiLCAvLyBcdTUzOEJcdTdGMjlcdTdCOTdcdTZDRDVcbiAgICAgIGV4dDogXCIuZ3pcIiwgLy8gXHU2NTg3XHU0RUY2XHU3QzdCXHU1NzhCXG4gICAgfSksXG4gIF07XG5cbiAgcmV0dXJuIHBsdWdpbnM7XG59XG4iLCAiY29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2Rpcm5hbWUgPSBcIkQ6XFxcXFBST0pFQ1RcXFxcRUxFQ18xMTI2XFxcXGZyb250XFxcXGRhdGEtbWFyay12M1xcXFxidWlsZFxcXFxwbHVnaW5zXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCJEOlxcXFxQUk9KRUNUXFxcXEVMRUNfMTEyNlxcXFxmcm9udFxcXFxkYXRhLW1hcmstdjNcXFxcYnVpbGRcXFxccGx1Z2luc1xcXFxyb3V0ZXIudHNcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfaW1wb3J0X21ldGFfdXJsID0gXCJmaWxlOi8vL0Q6L1BST0pFQ1QvRUxFQ18xMTI2L2Zyb250L2RhdGEtbWFyay12My9idWlsZC9wbHVnaW5zL3JvdXRlci50c1wiO2ltcG9ydCB0eXBlIHsgUm91dGVNZXRhIH0gZnJvbSAndnVlLXJvdXRlcic7XG5pbXBvcnQgRWxlZ2FudFZ1ZVJvdXRlciBmcm9tICdAZWxlZ2FudC1yb3V0ZXIvdnVlL3ZpdGUnO1xuaW1wb3J0IHR5cGUgeyBSb3V0ZUtleSB9IGZyb20gJ0BlbGVnYW50LXJvdXRlci90eXBlcyc7XG5cbmV4cG9ydCBmdW5jdGlvbiBzZXR1cEVsZWdhbnRSb3V0ZXIoKSB7XG4gIHJldHVybiBFbGVnYW50VnVlUm91dGVyKHtcbiAgICBsYXlvdXRzOiB7XG4gICAgICBiYXNlOiAnc3JjL2xheW91dHMvYmFzZS1sYXlvdXQvaW5kZXgudnVlJyxcbiAgICAgIGJsYW5rOiAnc3JjL2xheW91dHMvYmxhbmstbGF5b3V0L2luZGV4LnZ1ZSdcbiAgICB9LFxuICAgIGN1c3RvbVJvdXRlczoge1xuICAgICAgbmFtZXM6IFtcbiAgICAgICAgJ2V4Y2VwdGlvbl80MDMnLFxuICAgICAgICAnZXhjZXB0aW9uXzQwNCcsXG4gICAgICAgICdleGNlcHRpb25fNTAwJyxcbiAgICAgICAgJ2RvY3VtZW50X3Byb2plY3QnLFxuICAgICAgICAnZG9jdW1lbnRfcHJvamVjdC1saW5rJyxcbiAgICAgICAgJ2RvY3VtZW50X3Z1ZScsXG4gICAgICAgICdkb2N1bWVudF92aXRlJyxcbiAgICAgICAgJ2RvY3VtZW50X3Vub2NzcycsXG4gICAgICAgICdkb2N1bWVudF9uYWl2ZScsXG4gICAgICAgICdkb2N1bWVudF9hbnRkJ1xuICAgICAgXVxuICAgIH0sXG4gICAgcm91dGVQYXRoVHJhbnNmb3JtZXIocm91dGVOYW1lLCByb3V0ZVBhdGgpIHtcbiAgICAgIGNvbnN0IGtleSA9IHJvdXRlTmFtZSBhcyBSb3V0ZUtleTtcblxuICAgICAgaWYgKGtleSA9PT0gJ2xvZ2luJykge1xuICAgICAgICBjb25zdCBtb2R1bGVzOiBVbmlvbktleS5Mb2dpbk1vZHVsZVtdID0gWydwd2QtbG9naW4nLCAnY29kZS1sb2dpbicsICdyZWdpc3RlcicsICdyZXNldC1wd2QnLCAnYmluZC13ZWNoYXQnXTtcblxuICAgICAgICBjb25zdCBtb2R1bGVSZWcgPSBtb2R1bGVzLmpvaW4oJ3wnKTtcblxuICAgICAgICByZXR1cm4gYC9sb2dpbi86bW9kdWxlKCR7bW9kdWxlUmVnfSk/YDtcbiAgICAgIH1cblxuICAgICAgcmV0dXJuIHJvdXRlUGF0aDtcbiAgICB9LFxuICAgIG9uUm91dGVNZXRhR2VuKHJvdXRlTmFtZSkge1xuICAgICAgY29uc3Qga2V5ID0gcm91dGVOYW1lIGFzIFJvdXRlS2V5O1xuXG4gICAgICBjb25zdCBjb25zdGFudFJvdXRlczogUm91dGVLZXlbXSA9IFsnbG9naW4nLCAnNDAzJywgJzQwNCcsICc1MDAnXTtcblxuICAgICAgY29uc3QgbWV0YTogUGFydGlhbDxSb3V0ZU1ldGE+ID0ge1xuICAgICAgICB0aXRsZToga2V5LFxuICAgICAgICBpMThuS2V5OiBgcm91dGUuJHtrZXl9YCBhcyBBcHAuSTE4bi5JMThuS2V5XG4gICAgICB9O1xuXG4gICAgICBpZiAoY29uc3RhbnRSb3V0ZXMuaW5jbHVkZXMoa2V5KSkge1xuICAgICAgICBtZXRhLmNvbnN0YW50ID0gdHJ1ZTtcbiAgICAgIH1cblxuICAgICAgcmV0dXJuIG1ldGE7XG4gICAgfVxuICB9KTtcbn1cbiIsICJjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZGlybmFtZSA9IFwiRDpcXFxcUFJPSkVDVFxcXFxFTEVDXzExMjZcXFxcZnJvbnRcXFxcZGF0YS1tYXJrLXYzXFxcXGJ1aWxkXFxcXHBsdWdpbnNcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIkQ6XFxcXFBST0pFQ1RcXFxcRUxFQ18xMTI2XFxcXGZyb250XFxcXGRhdGEtbWFyay12M1xcXFxidWlsZFxcXFxwbHVnaW5zXFxcXHVub2Nzcy50c1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vRDovUFJPSkVDVC9FTEVDXzExMjYvZnJvbnQvZGF0YS1tYXJrLXYzL2J1aWxkL3BsdWdpbnMvdW5vY3NzLnRzXCI7aW1wb3J0IHByb2Nlc3MgZnJvbSAnbm9kZTpwcm9jZXNzJztcbmltcG9ydCBwYXRoIGZyb20gJ25vZGU6cGF0aCc7XG5pbXBvcnQgdW5vY3NzIGZyb20gJ0B1bm9jc3Mvdml0ZSc7XG5pbXBvcnQgcHJlc2V0SWNvbnMgZnJvbSAnQHVub2Nzcy9wcmVzZXQtaWNvbnMnO1xuaW1wb3J0IHsgRmlsZVN5c3RlbUljb25Mb2FkZXIgfSBmcm9tICdAaWNvbmlmeS91dGlscy9saWIvbG9hZGVyL25vZGUtbG9hZGVycyc7XG5cbmV4cG9ydCBmdW5jdGlvbiBzZXR1cFVub2Nzcyh2aXRlRW52OiBFbnYuSW1wb3J0TWV0YSkge1xuICBjb25zdCB7IFZJVEVfSUNPTl9QUkVGSVgsIFZJVEVfSUNPTl9MT0NBTF9QUkVGSVggfSA9IHZpdGVFbnY7XG5cbiAgY29uc3QgbG9jYWxJY29uUGF0aCA9IHBhdGguam9pbihwcm9jZXNzLmN3ZCgpLCAnc3JjL2Fzc2V0cy9zdmctaWNvbicpO1xuXG4gIC8qKiBUaGUgbmFtZSBvZiB0aGUgbG9jYWwgaWNvbiBjb2xsZWN0aW9uICovXG4gIGNvbnN0IGNvbGxlY3Rpb25OYW1lID0gVklURV9JQ09OX0xPQ0FMX1BSRUZJWC5yZXBsYWNlKGAke1ZJVEVfSUNPTl9QUkVGSVh9LWAsICcnKTtcblxuICByZXR1cm4gdW5vY3NzKHtcbiAgICBwcmVzZXRzOiBbXG4gICAgICBwcmVzZXRJY29ucyh7XG4gICAgICAgIHByZWZpeDogYCR7VklURV9JQ09OX1BSRUZJWH0tYCxcbiAgICAgICAgc2NhbGU6IDEsXG4gICAgICAgIGV4dHJhUHJvcGVydGllczoge1xuICAgICAgICAgIGRpc3BsYXk6ICdpbmxpbmUtYmxvY2snXG4gICAgICAgIH0sXG4gICAgICAgIGNvbGxlY3Rpb25zOiB7XG4gICAgICAgICAgW2NvbGxlY3Rpb25OYW1lXTogRmlsZVN5c3RlbUljb25Mb2FkZXIobG9jYWxJY29uUGF0aCwgc3ZnID0+XG4gICAgICAgICAgICBzdmcucmVwbGFjZSgvXjxzdmdcXHMvLCAnPHN2ZyB3aWR0aD1cIjFlbVwiIGhlaWdodD1cIjFlbVwiICcpXG4gICAgICAgICAgKVxuICAgICAgICB9LFxuICAgICAgICB3YXJuOiB0cnVlXG4gICAgICB9KVxuICAgIF1cbiAgfSk7XG59XG4iLCAiY29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2Rpcm5hbWUgPSBcIkQ6XFxcXFBST0pFQ1RcXFxcRUxFQ18xMTI2XFxcXGZyb250XFxcXGRhdGEtbWFyay12M1xcXFxidWlsZFxcXFxwbHVnaW5zXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCJEOlxcXFxQUk9KRUNUXFxcXEVMRUNfMTEyNlxcXFxmcm9udFxcXFxkYXRhLW1hcmstdjNcXFxcYnVpbGRcXFxccGx1Z2luc1xcXFx1bnBsdWdpbi50c1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vRDovUFJPSkVDVC9FTEVDXzExMjYvZnJvbnQvZGF0YS1tYXJrLXYzL2J1aWxkL3BsdWdpbnMvdW5wbHVnaW4udHNcIjtpbXBvcnQgcHJvY2VzcyBmcm9tICdub2RlOnByb2Nlc3MnO1xuaW1wb3J0IHBhdGggZnJvbSAnbm9kZTpwYXRoJztcbmltcG9ydCB0eXBlIHsgUGx1Z2luT3B0aW9uIH0gZnJvbSAndml0ZSc7XG5pbXBvcnQgSWNvbnMgZnJvbSAndW5wbHVnaW4taWNvbnMvdml0ZSc7XG5pbXBvcnQgSWNvbnNSZXNvbHZlciBmcm9tICd1bnBsdWdpbi1pY29ucy9yZXNvbHZlcic7XG5pbXBvcnQgQ29tcG9uZW50cyBmcm9tICd1bnBsdWdpbi12dWUtY29tcG9uZW50cy92aXRlJztcbmltcG9ydCB7IEFudERlc2lnblZ1ZVJlc29sdmVyLCBOYWl2ZVVpUmVzb2x2ZXIgfSBmcm9tICd1bnBsdWdpbi12dWUtY29tcG9uZW50cy9yZXNvbHZlcnMnO1xuaW1wb3J0IHsgRmlsZVN5c3RlbUljb25Mb2FkZXIgfSBmcm9tICd1bnBsdWdpbi1pY29ucy9sb2FkZXJzJztcbmltcG9ydCB7IGNyZWF0ZVN2Z0ljb25zUGx1Z2luIH0gZnJvbSAndml0ZS1wbHVnaW4tc3ZnLWljb25zJztcblxuZXhwb3J0IGZ1bmN0aW9uIHNldHVwVW5wbHVnaW4odml0ZUVudjogRW52LkltcG9ydE1ldGEpIHtcbiAgY29uc3QgeyBWSVRFX0lDT05fUFJFRklYLCBWSVRFX0lDT05fTE9DQUxfUFJFRklYIH0gPSB2aXRlRW52O1xuXG4gIGNvbnN0IGxvY2FsSWNvblBhdGggPSBwYXRoLmpvaW4ocHJvY2Vzcy5jd2QoKSwgJ3NyYy9hc3NldHMvc3ZnLWljb24nKTtcblxuICAvKiogVGhlIG5hbWUgb2YgdGhlIGxvY2FsIGljb24gY29sbGVjdGlvbiAqL1xuICBjb25zdCBjb2xsZWN0aW9uTmFtZSA9IFZJVEVfSUNPTl9MT0NBTF9QUkVGSVgucmVwbGFjZShgJHtWSVRFX0lDT05fUFJFRklYfS1gLCAnJyk7XG5cbiAgY29uc3QgcGx1Z2luczogUGx1Z2luT3B0aW9uW10gPSBbXG4gICAgSWNvbnMoe1xuICAgICAgY29tcGlsZXI6ICd2dWUzJyxcbiAgICAgIGN1c3RvbUNvbGxlY3Rpb25zOiB7XG4gICAgICAgIFtjb2xsZWN0aW9uTmFtZV06IEZpbGVTeXN0ZW1JY29uTG9hZGVyKGxvY2FsSWNvblBhdGgsIHN2ZyA9PlxuICAgICAgICAgIHN2Zy5yZXBsYWNlKC9ePHN2Z1xccy8sICc8c3ZnIHdpZHRoPVwiMWVtXCIgaGVpZ2h0PVwiMWVtXCIgJylcbiAgICAgICAgKVxuICAgICAgfSxcbiAgICAgIHNjYWxlOiAxLFxuICAgICAgZGVmYXVsdENsYXNzOiAnaW5saW5lLWJsb2NrJ1xuICAgIH0pLFxuICAgIENvbXBvbmVudHMoe1xuICAgICAgZHRzOiAnc3JjL3R5cGluZ3MvY29tcG9uZW50cy5kLnRzJyxcbiAgICAgIHR5cGVzOiBbeyBmcm9tOiAndnVlLXJvdXRlcicsIG5hbWVzOiBbJ1JvdXRlckxpbmsnLCAnUm91dGVyVmlldyddIH1dLFxuICAgICAgcmVzb2x2ZXJzOiBbXG4gICAgICAgIEFudERlc2lnblZ1ZVJlc29sdmVyKHtcbiAgICAgICAgICBpbXBvcnRTdHlsZTogZmFsc2VcbiAgICAgICAgfSksXG4gICAgICAgIE5haXZlVWlSZXNvbHZlcigpLFxuICAgICAgICBJY29uc1Jlc29sdmVyKHsgY3VzdG9tQ29sbGVjdGlvbnM6IFtjb2xsZWN0aW9uTmFtZV0sIGNvbXBvbmVudFByZWZpeDogVklURV9JQ09OX1BSRUZJWCB9KVxuICAgICAgXVxuICAgIH0pLFxuICAgIGNyZWF0ZVN2Z0ljb25zUGx1Z2luKHtcbiAgICAgIGljb25EaXJzOiBbbG9jYWxJY29uUGF0aF0sXG4gICAgICBzeW1ib2xJZDogYCR7VklURV9JQ09OX0xPQ0FMX1BSRUZJWH0tW2Rpcl0tW25hbWVdYCxcbiAgICAgIGluamVjdDogJ2JvZHktbGFzdCcsXG4gICAgICBjdXN0b21Eb21JZDogJ19fU1ZHX0lDT05fTE9DQUxfXydcbiAgICB9KVxuICBdO1xuXG4gIHJldHVybiBwbHVnaW5zO1xufVxuIiwgImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJEOlxcXFxQUk9KRUNUXFxcXEVMRUNfMTEyNlxcXFxmcm9udFxcXFxkYXRhLW1hcmstdjNcXFxcYnVpbGRcXFxccGx1Z2luc1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9maWxlbmFtZSA9IFwiRDpcXFxcUFJPSkVDVFxcXFxFTEVDXzExMjZcXFxcZnJvbnRcXFxcZGF0YS1tYXJrLXYzXFxcXGJ1aWxkXFxcXHBsdWdpbnNcXFxcaHRtbC50c1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vRDovUFJPSkVDVC9FTEVDXzExMjYvZnJvbnQvZGF0YS1tYXJrLXYzL2J1aWxkL3BsdWdpbnMvaHRtbC50c1wiO2ltcG9ydCB0eXBlIHsgUGx1Z2luIH0gZnJvbSAndml0ZSc7XG5cbmV4cG9ydCBmdW5jdGlvbiBzZXR1cEh0bWxQbHVnaW4oYnVpbGRUaW1lOiBzdHJpbmcpIHtcbiAgY29uc3QgcGx1Z2luOiBQbHVnaW4gPSB7XG4gICAgbmFtZTogJ2h0bWwtcGx1Z2luJyxcbiAgICBhcHBseTogJ2J1aWxkJyxcbiAgICB0cmFuc2Zvcm1JbmRleEh0bWwoaHRtbCkge1xuICAgICAgcmV0dXJuIGh0bWwucmVwbGFjZSgnPGhlYWQ+JywgYDxoZWFkPlxcbiAgICA8bWV0YSBuYW1lPVwiYnVpbGRUaW1lXCIgY29udGVudD1cIiR7YnVpbGRUaW1lfVwiPmApO1xuICAgIH1cbiAgfTtcblxuICByZXR1cm4gcGx1Z2luO1xufVxuIiwgImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJEOlxcXFxQUk9KRUNUXFxcXEVMRUNfMTEyNlxcXFxmcm9udFxcXFxkYXRhLW1hcmstdjNcXFxcc3JjXFxcXHV0aWxzXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCJEOlxcXFxQUk9KRUNUXFxcXEVMRUNfMTEyNlxcXFxmcm9udFxcXFxkYXRhLW1hcmstdjNcXFxcc3JjXFxcXHV0aWxzXFxcXHNlcnZpY2UudHNcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfaW1wb3J0X21ldGFfdXJsID0gXCJmaWxlOi8vL0Q6L1BST0pFQ1QvRUxFQ18xMTI2L2Zyb250L2RhdGEtbWFyay12My9zcmMvdXRpbHMvc2VydmljZS50c1wiOy8qKlxuICogQ3JlYXRlIHNlcnZpY2UgY29uZmlnIGJ5IGN1cnJlbnQgZW52XG4gKlxuICogQHBhcmFtIGVudiBUaGUgY3VycmVudCBlbnZcbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGNyZWF0ZVNlcnZpY2VDb25maWcoZW52OiBFbnYuSW1wb3J0TWV0YSkge1xuICBjb25zdCB7IFZJVEVfU0VSVklDRV9CQVNFX1VSTCwgVklURV9PVEhFUl9TRVJWSUNFX0JBU0VfVVJMIH0gPSBlbnY7XG5cbiAgbGV0IG90aGVyID0ge30gYXMgUmVjb3JkPEFwcC5TZXJ2aWNlLk90aGVyQmFzZVVSTEtleSwgc3RyaW5nPjtcbiAgdHJ5IHtcbiAgICBvdGhlciA9IEpTT04ucGFyc2UoVklURV9PVEhFUl9TRVJWSUNFX0JBU0VfVVJMKTtcbiAgfSBjYXRjaCAoZXJyb3IpIHtcbiAgICAvLyBlc2xpbnQtZGlzYWJsZS1uZXh0LWxpbmUgbm8tY29uc29sZVxuICAgIGNvbnNvbGUuZXJyb3IoJ1ZJVEVfT1RIRVJfU0VSVklDRV9CQVNFX1VSTCBpcyBub3QgYSB2YWxpZCBKU09OIHN0cmluZycpO1xuICB9XG5cbiAgY29uc3QgaHR0cENvbmZpZzogQXBwLlNlcnZpY2UuU2ltcGxlU2VydmljZUNvbmZpZyA9IHtcbiAgICBiYXNlVVJMOiBWSVRFX1NFUlZJQ0VfQkFTRV9VUkwsXG4gICAgb3RoZXJcbiAgfTtcblxuICBjb25zdCBvdGhlckh0dHBLZXlzID0gT2JqZWN0LmtleXMoaHR0cENvbmZpZy5vdGhlcikgYXMgQXBwLlNlcnZpY2UuT3RoZXJCYXNlVVJMS2V5W107XG5cbiAgY29uc3Qgb3RoZXJDb25maWc6IEFwcC5TZXJ2aWNlLk90aGVyU2VydmljZUNvbmZpZ0l0ZW1bXSA9IG90aGVySHR0cEtleXMubWFwKGtleSA9PiB7XG4gICAgcmV0dXJuIHtcbiAgICAgIGtleSxcbiAgICAgIGJhc2VVUkw6IGh0dHBDb25maWcub3RoZXJba2V5XSxcbiAgICAgIHByb3h5UGF0dGVybjogY3JlYXRlUHJveHlQYXR0ZXJuKGtleSlcbiAgICB9O1xuICB9KTtcblxuICBjb25zdCBjb25maWc6IEFwcC5TZXJ2aWNlLlNlcnZpY2VDb25maWcgPSB7XG4gICAgYmFzZVVSTDogaHR0cENvbmZpZy5iYXNlVVJMLFxuICAgIHByb3h5UGF0dGVybjogY3JlYXRlUHJveHlQYXR0ZXJuKCksXG4gICAgb3RoZXI6IG90aGVyQ29uZmlnXG4gIH07XG5cbiAgcmV0dXJuIGNvbmZpZztcbn1cblxuLyoqXG4gKiBnZXQgYmFja2VuZCBzZXJ2aWNlIGJhc2UgdXJsXG4gKlxuICogQHBhcmFtIGVudiAtIHRoZSBjdXJyZW50IGVudlxuICogQHBhcmFtIGlzUHJveHkgLSBpZiB1c2UgcHJveHlcbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGdldFNlcnZpY2VCYXNlVVJMKGVudjogRW52LkltcG9ydE1ldGEsIGlzUHJveHk6IGJvb2xlYW4pIHtcbiAgY29uc3QgeyBiYXNlVVJMLCBvdGhlciB9ID0gY3JlYXRlU2VydmljZUNvbmZpZyhlbnYpO1xuXG4gIGNvbnN0IG90aGVyQmFzZVVSTCA9IHt9IGFzIFJlY29yZDxBcHAuU2VydmljZS5PdGhlckJhc2VVUkxLZXksIHN0cmluZz47XG5cbiAgb3RoZXIuZm9yRWFjaChpdGVtID0+IHtcbiAgICBvdGhlckJhc2VVUkxbaXRlbS5rZXldID0gaXNQcm94eSA/IGl0ZW0ucHJveHlQYXR0ZXJuIDogaXRlbS5iYXNlVVJMO1xuICB9KTtcblxuICByZXR1cm4ge1xuICAgIGJhc2VVUkw6IGlzUHJveHkgPyBjcmVhdGVQcm94eVBhdHRlcm4oKSA6IGJhc2VVUkwsXG4gICAgb3RoZXJCYXNlVVJMXG4gIH07XG59XG5cbi8qKlxuICogR2V0IHByb3h5IHBhdHRlcm4gb2YgYmFja2VuZCBzZXJ2aWNlIGJhc2UgdXJsXG4gKlxuICogQHBhcmFtIGtleSBJZiBub3Qgc2V0LCB3aWxsIHVzZSB0aGUgZGVmYXVsdCBrZXlcbiAqL1xuZnVuY3Rpb24gY3JlYXRlUHJveHlQYXR0ZXJuKGtleT86IEFwcC5TZXJ2aWNlLk90aGVyQmFzZVVSTEtleSkge1xuICBpZiAoIWtleSkge1xuICAgIHJldHVybiAnL3Byb3h5LWRlZmF1bHQnO1xuICB9XG5cbiAgcmV0dXJuIGAvcHJveHktJHtrZXl9YDtcbn1cbiIsICJjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZGlybmFtZSA9IFwiRDpcXFxcUFJPSkVDVFxcXFxFTEVDXzExMjZcXFxcZnJvbnRcXFxcZGF0YS1tYXJrLXYzXFxcXGJ1aWxkXFxcXGNvbmZpZ1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9maWxlbmFtZSA9IFwiRDpcXFxcUFJPSkVDVFxcXFxFTEVDXzExMjZcXFxcZnJvbnRcXFxcZGF0YS1tYXJrLXYzXFxcXGJ1aWxkXFxcXGNvbmZpZ1xcXFxwcm94eS50c1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vRDovUFJPSkVDVC9FTEVDXzExMjYvZnJvbnQvZGF0YS1tYXJrLXYzL2J1aWxkL2NvbmZpZy9wcm94eS50c1wiO2ltcG9ydCB0eXBlIHsgUHJveHlPcHRpb25zIH0gZnJvbSBcInZpdGVcIjtcbmltcG9ydCB7IGNyZWF0ZVNlcnZpY2VDb25maWcgfSBmcm9tIFwiLi4vLi4vc3JjL3V0aWxzL3NlcnZpY2VcIjtcblxuLyoqXG4gKiBTZXQgaHR0cCBwcm94eVxuICpcbiAqIEBwYXJhbSBlbnYgLSBUaGUgY3VycmVudCBlbnZcbiAqIEBwYXJhbSBpc0RldiAtIElzIGRldmVsb3BtZW50IGVudmlyb25tZW50XG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBjcmVhdGVWaXRlUHJveHkoZW52OiBFbnYuSW1wb3J0TWV0YSwgaXNEZXY6IGJvb2xlYW4pIHtcbiAgY29uc3QgaXNFbmFibGVIdHRwUHJveHkgPSBpc0RldiAmJiBlbnYuVklURV9IVFRQX1BST1hZID09PSBcIllcIjtcbiAgaWYgKCFpc0VuYWJsZUh0dHBQcm94eSkgcmV0dXJuIHVuZGVmaW5lZDtcblxuICBjb25zdCB7IGJhc2VVUkwsIHByb3h5UGF0dGVybiwgb3RoZXIgfSA9IGNyZWF0ZVNlcnZpY2VDb25maWcoZW52KTtcblxuICBjb25zdCBwcm94eTogUmVjb3JkPHN0cmluZywgUHJveHlPcHRpb25zPiA9IGNyZWF0ZVByb3h5SXRlbSh7XG4gICAgYmFzZVVSTCxcbiAgICBwcm94eVBhdHRlcm4sXG4gIH0pO1xuXG4gIG90aGVyLmZvckVhY2goKGl0ZW0pID0+IHtcbiAgICBPYmplY3QuYXNzaWduKHByb3h5LCBjcmVhdGVQcm94eUl0ZW0oaXRlbSkpO1xuICB9KTtcblxuICByZXR1cm4gcHJveHk7XG59XG5cbmZ1bmN0aW9uIGNyZWF0ZVByb3h5SXRlbShpdGVtOiBBcHAuU2VydmljZS5TZXJ2aWNlQ29uZmlnSXRlbSkge1xuICBjb25zdCBwcm94eTogUmVjb3JkPHN0cmluZywgUHJveHlPcHRpb25zPiA9IHt9O1xuXG4gIHByb3h5W2l0ZW0ucHJveHlQYXR0ZXJuXSA9IHtcbiAgICB0YXJnZXQ6IGl0ZW0uYmFzZVVSTCxcbiAgICBjaGFuZ2VPcmlnaW46IHRydWUsXG4gICAgcmV3cml0ZTogKHBhdGgpID0+IHBhdGgucmVwbGFjZShuZXcgUmVnRXhwKGBeJHtpdGVtLnByb3h5UGF0dGVybn1gKSwgXCJcIiksXG4gIH07XG5cbiAgcmV0dXJuIHByb3h5O1xufVxuIiwgImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJEOlxcXFxQUk9KRUNUXFxcXEVMRUNfMTEyNlxcXFxmcm9udFxcXFxkYXRhLW1hcmstdjNcXFxcYnVpbGRcXFxcY29uZmlnXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCJEOlxcXFxQUk9KRUNUXFxcXEVMRUNfMTEyNlxcXFxmcm9udFxcXFxkYXRhLW1hcmstdjNcXFxcYnVpbGRcXFxcY29uZmlnXFxcXHRpbWUudHNcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfaW1wb3J0X21ldGFfdXJsID0gXCJmaWxlOi8vL0Q6L1BST0pFQ1QvRUxFQ18xMTI2L2Zyb250L2RhdGEtbWFyay12My9idWlsZC9jb25maWcvdGltZS50c1wiO2ltcG9ydCBkYXlqcyBmcm9tICdkYXlqcyc7XG5pbXBvcnQgdXRjIGZyb20gJ2RheWpzL3BsdWdpbi91dGMnO1xuaW1wb3J0IHRpbWV6b25lIGZyb20gJ2RheWpzL3BsdWdpbi90aW1lem9uZSc7XG5cbmV4cG9ydCBmdW5jdGlvbiBnZXRCdWlsZFRpbWUoKSB7XG4gIGRheWpzLmV4dGVuZCh1dGMpO1xuICBkYXlqcy5leHRlbmQodGltZXpvbmUpO1xuXG4gIGNvbnN0IGJ1aWxkVGltZSA9IGRheWpzLnR6KERhdGUubm93KCksICdBc2lhL1NoYW5naGFpJykuZm9ybWF0KCdZWVlZLU1NLUREIEhIOm1tOnNzJyk7XG5cbiAgcmV0dXJuIGJ1aWxkVGltZTtcbn1cbiJdLAogICJtYXBwaW5ncyI6ICI7QUFBaVQsT0FBT0EsY0FBYTtBQUNyVSxTQUFTLEtBQUsscUJBQXFCO0FBQ25DLFNBQVMsY0FBYyxlQUFlOzs7QUNEdEMsT0FBTyxTQUFTO0FBQ2hCLE9BQU8sWUFBWTtBQUNuQixPQUFPLGlCQUFpQjtBQUN4QixPQUFPLGNBQWM7OztBQ0hyQixPQUFPLHNCQUFzQjtBQUd0QixTQUFTLHFCQUFxQjtBQUNuQyxTQUFPLGlCQUFpQjtBQUFBLElBQ3RCLFNBQVM7QUFBQSxNQUNQLE1BQU07QUFBQSxNQUNOLE9BQU87QUFBQSxJ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QTtBQUFBLFVBQ2hCLGdCQUFnQjtBQUFBO0FBQUE7QUFBQTtBQUFBLFVBR2hCLGVBQWUsWUFBWTtBQUV6QixnQkFBSSxXQUFXLE1BQU0sU0FBUyxNQUFNLEdBQUc7QUFDckMscUJBQU87QUFBQSxZQUNUO0FBRUEsa0JBQU0sV0FBVyxDQUFDLFFBQVEsUUFBUSxTQUFTLFVBQVUsTUFBTTtBQUMzRCxnQkFBSSxTQUFTLEtBQUssQ0FBQyxRQUFRLFdBQVcsTUFBTSxTQUFTLEdBQUcsQ0FBQyxHQUFHO0FBQzFELHFCQUFPO0FBQUEsWUFDVDtBQUdBLGtCQUFNLFVBQVUsQ0FBQyxRQUFRLFFBQVEsU0FBUyxTQUFTLFFBQVEsT0FBTztBQUNsRSxnQkFBSSxRQUFRLEtBQUssQ0FBQyxRQUFRLFdBQVcsTUFBTSxTQUFTLEdBQUcsQ0FBQyxHQUFHO0FBQ3pELHFCQUFPO0FBQUEsWUFDVDtBQUdBLGtCQUFNLFNBQVMsQ0FBQyxNQUFNO0FBQ3RCLGdCQUFJLE9BQU8sS0FBSyxDQUFDLFFBQVEsV0FBVyxNQUFNLFNBQVMsR0FBRyxDQUFDLEdBQUc7QUFDeEQscUJBQU87QUFBQSxZQUNUO0FBR0Esa0JBQU0sWUFBWSxDQUFDLFFBQVEsUUFBUSxRQUFRLFFBQVEsUUFBUSxNQUFNO0FBQ2pFLGdCQUFJLFVBQVUsS0FBSyxDQUFDLFFBQVEsV0FBVyxNQUFNLFNBQVMsR0FBRyxDQUFDLEdBQUc7QUFDM0QscUJBQU87QUFBQSxZQUNUO0FBRUEsbUJBQU87QUFBQSxVQUNUO0FBQUEsVUFDQSxhQUFhLElBQUk7QUFDZixnQkFBSSxHQUFHLFNBQVMsY0FBYyxHQUFHO0FBQy9CLHFCQUFPLEdBQ0osU0FBUyxFQUNULE1BQU0sZUFBZSxFQUFFLENBQUMsRUFDeEIsTUFBTSxHQUFHLEVBQUUsQ0FBQyxFQUNaLFNBQVM7QUFBQSxZQUNkO0FBQUEsVUFDRjtBQUFBLFFBQ0Y7QUFBQSxNQUNGO0FBQUE7QUFBQSxNQUVBLGVBQWU7QUFBQSxRQUNiLFVBQVU7QUFBQSxVQUNSLGNBQWM7QUFBQSxVQUNkLGVBQWU7QUFBQSxRQUNqQjtBQUFBLE1BQ0Y7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUNGLENBQUM7IiwKICAibmFtZXMiOiBbInByb2Nlc3MiLCAicHJvY2VzcyIsICJwYXRoIiwgIkZpbGVTeXN0ZW1JY29uTG9hZGVyIiwgInBhdGgiLCAicHJvY2VzcyIsICJGaWxlU3lzdGVtSWNvbkxvYWRlciIsICJwYXRoIiwgInByb2Nlc3MiXQp9Cg==
