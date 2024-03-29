import random
from django.db.models import Q, Count
from utils.api import APIView
from account.decorators import check_contest_permission, login_required
from ..models import ProblemTag, Problem, ProblemRuleType
from ..serializers import ProblemSerializer, TagSerializer, ProblemSafeSerializer, RecommendBonusProblemSerializer
from contest.models import ContestRuleType
from account.models import UserProfile
from submission.models import JudgeStatus
from django.http import HttpResponseNotFound
from utils.constants import ProblemScore


class ProblemTagAPI(APIView):
    def get(self, request):
        qs = ProblemTag.objects
        keyword = request.GET.get("keyword")
        if keyword:
            qs = ProblemTag.objects.filter(name__icontains=keyword)
        tags = qs.annotate(problem_count=Count("problem")).filter(problem_count__gt=0)
        return self.success(TagSerializer(tags, many=True).data)


class PickOneAPI(APIView):
    def get(self, request):
        problems = Problem.objects.filter(contest_id__isnull=True, visible=True)
        count = problems.count()
        if count == 0:
            return self.error("No problem to pick")
        return self.success(problems[random.randint(0, count - 1)]._id)


class BonusProblemAPI(APIView):
    def get(self, request):
        bonus_problems = Problem.objects.filter(contest_id__isnull=True, visible=True, is_bonus=True)
        if not bonus_problems:
            return HttpResponseNotFound("No bonus problem")
        return self.success(RecommendBonusProblemSerializer(bonus_problems, many=True).data)


class ProblemAPI(APIView):
    @staticmethod
    def _add_problem_status(request, queryset_values):
        if request.user.is_authenticated:
            profile = request.user.userprofile
            acm_problems_status = profile.acm_problems_status.get("problems", {})
            oi_problems_status = profile.oi_problems_status.get("problems", {})
            # paginate data
            results = queryset_values.get("results")
            if results is not None:
                problems = results
            else:
                problems = [queryset_values, ]
            for problem in problems:
                if problem["rule_type"] == ProblemRuleType.ACM:
                    problem["my_status"] = acm_problems_status.get(str(problem["id"]), {}).get("status")
                else:
                    problem["my_status"] = oi_problems_status.get(str(problem["id"]), {}).get("status")

    def get(self, request):
        # 问题详情页
        problem_id = request.GET.get("problem_id")
        if problem_id:
            try:
                problem = Problem.objects.select_related("created_by") \
                    .get(_id=problem_id, contest_id__isnull=True, visible=True)
                problem_data = ProblemSerializer(problem).data
                self._add_problem_status(request, problem_data)
                return self.success(problem_data)
            except Problem.DoesNotExist:
                return self.error("Problem does not exist")

        limit = request.GET.get("limit")
        if not limit:
            return self.error("Limit is needed")

        problems = Problem.objects.select_related("created_by").filter(contest_id__isnull=True, visible=True)
        # 按照标签筛选
        tag_text = request.GET.get("tag")
        if tag_text:
            problems = problems.filter(tags__name=tag_text)

        # 搜索的情况
        keyword = request.GET.get("keyword", "").strip()
        if keyword:
            problems = problems.filter(Q(title__icontains=keyword) | Q(_id__icontains=keyword))

        # 难度筛选
        difficulty = request.GET.get("difficulty")
        if difficulty:
            problems = problems.filter(difficulty=difficulty)

        field = request.GET.get("field")
        if field:
            problems = problems.filter(field=field)

        # 根据profile 为做过的题目添加标记
        data = self.paginate_data(request, problems, ProblemSerializer)
        self._add_problem_status(request, data)
        return self.success(data)


class ContestProblemAPI(APIView):
    def _add_problem_status(self, request, queryset_values):
        if request.user.is_authenticated:
            profile = request.user.userprofile
            if self.contest.rule_type == ContestRuleType.ACM:
                problems_status = profile.acm_problems_status.get("contest_problems", {})
            else:
                problems_status = profile.oi_problems_status.get("contest_problems", {})
            for problem in queryset_values:
                problem["my_status"] = problems_status.get(str(problem["id"]), {}).get("status")

    @check_contest_permission(check_type="problems")
    def get(self, request):
        problem_id = request.GET.get("problem_id")
        if problem_id:
            try:
                problem = Problem.objects.select_related("created_by").get(_id=problem_id,
                                                                           contest=self.contest,
                                                                           visible=True)
            except Problem.DoesNotExist:
                return self.error("Problem does not exist.")
            if self.contest.problem_details_permission(request.user):
                problem_data = ProblemSerializer(problem).data
                self._add_problem_status(request, [problem_data, ])
            else:
                problem_data = ProblemSafeSerializer(problem).data
            return self.success(problem_data)

        contest_problems = Problem.objects.select_related("created_by").filter(contest=self.contest, visible=True)
        if self.contest.problem_details_permission(request.user):
            data = ProblemSerializer(contest_problems, many=True).data
            self._add_problem_status(request, data)
        else:
            data = ProblemSafeSerializer(contest_problems, many=True).data
        return self.success(data)


def get_user_solved_problems(user):
    solved_problems = UserProfile.objects.get(user=user).acm_problems_status.get("problems", {})
    return [v['_id'] for k, v in solved_problems.items() if v['status'] == JudgeStatus.ACCEPTED]


class AIRecommendProblemAPI(APIView):
    @login_required
    def get(self, request):
        try:
            field_score = UserProfile.objects.get(user=request.user).field_score
            field_score['max_score'] = ProblemScore.score['VeryHigh'] * 20

            weak_field = 0
            weak_field_score = field_score['0']
            for k, v in field_score.items():
                field_score[k] = min(v, field_score['max_score'])
                if field_score[k] < weak_field_score:
                    weak_field = k
                    weak_field_score = field_score[k]

            # remove if the user has solved the problem
            unresolved_problems = Problem.objects.filter(field=weak_field, visible=True)\
                .exclude(_id__in=get_user_solved_problems(request.user))
            unresolved_problems = random.sample(list(unresolved_problems), min(3, unresolved_problems.count()))
            recommend_problems = RecommendBonusProblemSerializer(unresolved_problems, many=True).data

            return self.success({"field_score": field_score, "recommend_problems": recommend_problems})
        except UserProfile.DoesNotExist:
            return HttpResponseNotFound("User does not exist")
