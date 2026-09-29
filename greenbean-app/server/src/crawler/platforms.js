// 쇼핑몰 플랫폼별 규칙. 국내 생두몰은 대부분 Cafe24 / 고도몰 / 영카트 / 위사 / 메이크샵 / 아임웹 위에서 돈다.
// 스킨(디자인)은 몰마다 다르지만 '상품 링크 주소 모양'은 플랫폼마다 고정이라, 링크를 기준으로 상품 카드를 찾는다.

export const PLATFORMS = {
  cafe24: {
    // /product/상품명/123/category/64/display/1/  또는  /product/detail.html?product_no=123
    idFromHref(href) {
      const m = href.match(/\/product\/(?:[^/?#]+\/)?(\d+)\/category\/\d+/) || href.match(/\/product\/detail\.html\?(?:[^#]*&)?product_no=(\d+)/);
      return m ? m[1] : null;
    },
    canonicalUrl: (origin, id) => `${origin}/product/detail.html?product_no=${id}`,
    // 목록 페이지의 카테고리 번호. 상품 링크에도 카테고리가 붙어 있어서, 배너·추천상품 같은 다른 카테고리 상품을 거를 수 있다.
    listCategory(pageUrl) {
      const u = new URL(pageUrl);
      return u.searchParams.get('cate_no') || u.pathname.match(/\/category\/[^/]+\/(\d+)/)?.[1] || null;
    },
    hrefInCategory: (href, cat) => new RegExp(`(/category/${cat}/|[?&]cate_no=${cat}(&|$))`).test(href),
  },
  godomall: {
    idFromHref(href) {
      const m = href.match(/goods_view\.php\?(?:[^#]*&)?goodsNo=(\d+)/);
      return m ? m[1] : null;
    },
    canonicalUrl: (origin, id) => `${origin}/goods/goods_view.php?goodsNo=${id}`,
  },
  youngcart: {
    idFromHref(href) {
      const m = href.match(/shop\/item\.php\?(?:[^#]*&)?it_id=([\w-]+)/);
      return m ? m[1] : null;
    },
    canonicalUrl: (origin, id) => `${origin}/shop/item.php?it_id=${id}`,
  },
  wisa: {
    idFromHref(href) {
      const m = href.match(/shop\/detail\.php\?(?:[^#]*&)?pno=([0-9A-Za-z]+)/);
      return m ? m[1] : null;
    },
    canonicalUrl: (origin, id) => `${origin}/shop/detail.php?pno=${id}`,
  },
  makeshop: {
    idFromHref(href) {
      const m = href.match(/shopdetail\.html\?(?:[^#]*&)?branduid=(\d+)/);
      return m ? m[1] : null;
    },
    canonicalUrl: (origin, id) => `${origin}/shop/shopdetail.html?branduid=${id}`,
  },
  imweb: {
    // /37/?idx=123 — 게시판 글(bmode=view)은 상품이 아니다
    idFromHref(href) {
      if (/bmode=|t=board/.test(href)) return null;
      const m = href.match(/[?&]idx=(\d+)/);
      return m ? m[1] : null;
    },
    canonicalUrl: null, // 메뉴 경로가 몰마다 달라서 원래 링크를 그대로 쓴다
  },
};

export function getPlatform(name) {
  const p = PLATFORMS[name];
  if (!p) throw new Error(`알 수 없는 플랫폼: ${name}`);
  return p;
}
