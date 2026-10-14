# Proposed golden-set corrections (evidence from aether-bench reviews)

## discourse-graphite PR 8 — "The route provides the group's ID in params[:id], but the code reads params[:group_id]"

Wrong. In `config/routes.rb` the member routes are declared directly inside the `resources :groups` block
(not inside `member do` / `collection do`):

```ruby
resources :groups, constraints: AdminConstraint.new do
  collection do
    post "refresh_automatic_groups" => "groups#refresh_automatic_groups"
  end
  delete "members" => "groups#remove_member"
  put "members" => "groups#add_members"
end
```

Rails nests a bare route inside a `resources` block under the resource, so the paths are
`/admin/groups/:group_id/members`, and `params.require(:group_id)` in `add_members` / `remove_member`
is the correct key. Six independent review runs (Codex gpt-6-astra ×5, Claude Opus 5.5 ×1) each
examined this lead and concluded it holds; none reported the claimed failure.
