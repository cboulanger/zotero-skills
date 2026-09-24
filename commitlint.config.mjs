// Conventional Commits, enforced locally (husky commit-msg hook) and in CI.
// The commit type decides the next release: fix → patch, feat → minor,
// "!" after the type or a "BREAKING CHANGE:" footer → major.
export default {
  extends: ["@commitlint/config-conventional"],
  rules: {
    // release notes and pasted URLs make long lines legitimate
    "body-max-line-length": [0],
    "footer-max-line-length": [0],
  },
  ignores: [(message) => message.startsWith("chore(release):")],
};
